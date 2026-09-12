import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.api import app
from app.database import Base, get_db
from app.db_models import Lead
from app.models import LeadCreate
from app.scoring import score_lead
from tests.test_models import BASE


@pytest.fixture
def storage(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    factory = sessionmaker(engine, expire_on_commit=False)
    # Lifespan uses the same temporary engine; never initialize the developer DB.
    monkeypatch.setattr("app.api.engine", engine)

    def sessions():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = sessions
    try:
        with TestClient(app) as client:
            yield client, factory, engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_capture_retrieve_and_stored_qualification(storage):
    client, factory, _ = storage
    response = client.post("/leads", json=BASE)
    assert response.status_code == 201
    assert response.json()["created"] is True
    lead = response.json()["lead"]
    assert "dedup_key" not in lead
    assert lead["created_at"].endswith("Z")
    expected = score_lead(LeadCreate(**BASE))
    for field in ["lead_score", "qualification", "priority", "recommended_action"]:
        assert lead[field] == getattr(expected, field)
    assert client.get(f"/leads/{lead['id']}").json() == lead
    with factory() as db:
        stored = db.get(Lead, lead["id"])
        assert stored.dedup_key == hashlib.sha256(b"buyer@example.com|unspecified").hexdigest()
        assert stored.name == BASE["name"]
        assert db.scalar(select(func.count()).select_from(Lead)) == 1


@pytest.mark.parametrize("email", ["buyer@example.com", "BUYER@EXAMPLE.COM", "  Buyer@example.com  "])
@pytest.mark.parametrize("service", [None, "lead_generation"])
def test_duplicates_preserve_original(storage, email, service):
    client, _, _ = storage
    first = client.post("/leads", json=BASE | {"service_interest": service}).json()["lead"]
    second = client.post("/leads", json=BASE | {
        "email": email, "service_interest": service, "message": "We need a quote and a demo now.",
        "name": "Changed Buyer", "budget_range": "5000_plus",
    })
    assert second.status_code == 200
    assert second.json() == {"created": False, "lead": first}
    assert client.get("/leads").json() == [first]


def test_different_service_and_null_sentinel(storage):
    client, _, _ = storage
    first = client.post("/leads", json=BASE)
    assert client.post("/leads", json=BASE | {"service_interest": None}).status_code == 200
    other = client.post("/leads", json=BASE | {"service_interest": "other"})
    assert other.status_code == 201
    assert first.json()["lead"]["id"] != other.json()["lead"]["id"]
    assert len(client.get("/leads").json()) == 2


def test_missing_lead_and_empty_list(storage):
    client, _, _ = storage
    assert client.get("/leads").json() == []
    assert client.get("/leads/not-a-known-id").status_code == 404


@pytest.mark.parametrize("limit", [0, -1, 101, "bad"])
def test_invalid_limits(storage, limit):
    assert storage[0].get("/leads", params={"limit": limit}).status_code == 422


def test_list_limit_and_no_dedup_exposure(storage):
    client, _, _ = storage
    for service in [None, "other", "lead_generation"]:
        client.post("/leads", json=BASE | {"service_interest": service})
    rows = client.get("/leads?limit=2").json()
    assert len(rows) == 2
    assert all("dedup_key" not in row for row in rows)


def test_validation_and_qualify_never_insert(storage):
    client, factory, _ = storage
    assert client.post("/leads", json=BASE | {"email": "bad"}).status_code == 422
    assert client.post("/leads/qualify", json=BASE).status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Lead)) == 0


def test_database_unique_constraint(storage):
    client, factory, _ = storage
    lead_id = client.post("/leads", json=BASE).json()["lead"]["id"]
    with factory() as db:
        row = db.get(Lead, lead_id)
        clone = {col.name: getattr(row, col.name) for col in Lead.__table__.columns if col.name != "id"}
        db.add(Lead(**clone))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_uniqueness_race_recovers_after_rollback(storage):
    client, factory, engine = storage
    expected = client.post("/leads", json=BASE).json()["lead"]

    class RaceSession(Session):
        reads = 0
        rolled_back = False

        def scalar(self, *args, **kwargs):
            self.reads += 1
            if self.reads == 1:
                # Simulate a stale initial lookup; INSERT still hits real uniqueness.
                return None
            assert self.rolled_back
            return super().scalar(*args, **kwargs)

        def rollback(self):
            self.rolled_back = True
            return super().rollback()

    def sessions():
        with RaceSession(engine, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = sessions
    result = client.post("/leads", json=BASE)
    assert result.status_code == 200
    assert result.json() == {"created": False, "lead": expected}
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Lead)) == 1


@pytest.mark.parametrize("failure", [IntegrityError, OperationalError])
def test_database_failure_is_generic(storage, monkeypatch, failure):
    client, _, _ = storage

    def fail_commit(self):
        raise failure("private SQL", {}, Exception("private database location"))

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = client.post("/leads", json=BASE)
    assert response.status_code == 500
    assert response.json() == {"detail": "Database operation failed."}


def test_persistence_survives_new_connection(storage):
    client, factory, engine = storage
    lead_id = client.post("/leads", json=BASE).json()["lead"]["id"]
    engine.dispose()
    with factory() as db:
        assert db.get(Lead, lead_id).email == BASE["email"]
