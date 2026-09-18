"""Capture-level regressions: untrusted AI cannot replace lead identity or scoring."""
from datetime import datetime

import pytest

from app.models import LeadCreate
from app.scoring import score_lead
from tests.test_ai import STRONG, WARM, fake_sdk
from tests.test_persistence import storage


@pytest.mark.parametrize("injection", [
    {"name": "Injected Name"}, {"email": "injected@example.com"},
    {"lead_score": 999}, {"intent_strength": "invented"},
])
def test_invalid_ai_capture_preserves_identity_and_baseline(storage, monkeypatch, injection):
    _, sdk = fake_sdk(monkeypatch, payload=STRONG | injection)
    client = storage[0]
    response = client.post("/leads?use_ai=true", json=WARM)
    assert response.status_code == 201
    lead = response.json()["lead"]
    baseline = score_lead(LeadCreate(**WARM))
    assert lead["name"] == WARM["name"]
    assert lead["email"] == WARM["email"].lower()
    assert lead["ai_status"] == "fallback" and lead["ai_assessment"] is None
    assert lead["lead_score"] == baseline.lead_score
    assert lead["final_qualification"] == baseline.qualification
    assert lead["final_recommended_action"] == baseline.recommended_action
    assert "dedup_key" not in lead
    assert datetime.fromisoformat(lead["updated_at"]) >= datetime.fromisoformat(lead["created_at"])
    assert client.get(f"/leads/{lead['id']}").json() == lead
    duplicate = client.post("/leads?use_ai=true", json=WARM)
    assert duplicate.json() == {"created": False, "lead": lead}
    assert sdk.responses.parse.call_count == 1


def test_unknown_lead_response_does_not_echo_input(storage):
    response = storage[0].get("/leads/synthetic-private-marker")
    assert response.status_code == 404
    assert "synthetic-private-marker" not in response.text
    assert set(response.json()) == {"detail"}
