import pytest
from fastapi.testclient import TestClient

from app.api import app
from tests.test_models import BASE

client = TestClient(app)


def test_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Phililee AI Labs — Lead Generation Agent", "version": "1.0.0"}


def test_qualify():
    response = client.post("/leads/qualify", json=BASE)
    assert response.status_code == 200
    body = response.json()
    assert body["lead_score"] == 20
    assert body["qualification"] == "cold"
    assert body["priority"] == "low"
    assert body["recommended_action"] == "nurture"
    assert sum(body["score_breakdown"].values()) == 20
    assert set(body) == {"lead_score", "qualification", "priority", "recommended_action", "score_breakdown", "reasons"}


@pytest.mark.parametrize("changes", [
    {"email": "bad"}, {"name": "   "}, {"message": "short"},
    {"message": "   "}, {"source": "invalid"}, {"unexpected": True},
])
def test_validation_errors(changes):
    response = client.post("/leads/qualify", json=BASE | changes)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert "Traceback" not in response.text


def test_openapi_and_swagger():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["version"] == "1.0.0"
    assert schema["paths"]["/leads/qualify"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/LeadQualification")
    assert client.get("/docs").status_code == 200
