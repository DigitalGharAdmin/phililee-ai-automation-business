import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text

from app import ai_qualification as ai, settings
from app.api import app
from app.models import AILeadAssessment, LeadCreate, LeadStored
from app.scoring import score_lead
from tests.test_models import BASE
from tests.test_persistence import storage  # Reuse isolated SQLite fixture.

STRONG = dict(intent_strength="high", business_fit="excellent", urgency="high",
              decision_readiness="ready", ai_recommended_action="contact",
              summary="The inquiry signals commercial interest.", key_signals=["Explicit request"], risk_flags=[])
WEAK = STRONG | dict(intent_strength="low", business_fit="poor", decision_readiness="exploring")
WARM = BASE | dict(service_interest="other", budget_range="500_1000", timeline="within_3_months", company_size="2_10")
HOT = BASE | dict(service_interest="lead_generation", budget_range="5000_plus", timeline="immediate")


def fake_sdk(monkeypatch, payload=STRONG, error=None, status="completed"):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-placeholder")
    client = MagicMock()
    client.__enter__.return_value = client
    def parse(**kwargs):
        if error:
            raise error
        parsed = AILeadAssessment.model_validate(payload) if payload is not None else None
        return SimpleNamespace(status=status, output_parsed=parsed)
    client.responses.parse.side_effect = parse
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(ai, "OpenAI", constructor)
    return constructor, client


@pytest.mark.parametrize("lead,evidence,expected", [
    (BASE, STRONG, "warm"), (HOT, WEAK, "warm"), (WARM, STRONG, "hot"),
    (WARM, WEAK, "cold"), (HOT, STRONG, "hot"), (BASE, WEAK, "cold"),
    (WARM, STRONG | {"risk_flags": ["conflicting_information"]}, "warm"),
    (WARM, STRONG | {"decision_readiness": "considering"}, "warm"),
])
def test_reconciliation(lead, evidence, expected):
    baseline = score_lead(LeadCreate(**lead))
    result = ai.reconcile(baseline, AILeadAssessment(**evidence))
    assert result.deterministic == baseline
    assert result.final_qualification == expected
    priority, action = {"cold": ("low", "nurture"), "warm": ("medium", "review"), "hot": ("high", "contact")}[expected]
    assert (result.final_priority, result.final_recommended_action) == (priority, action)
    levels = ["cold", "warm", "hot"]
    assert abs(levels.index(expected) - levels.index(baseline.qualification)) <= 1


def test_success_privacy_and_request_options(monkeypatch, storage):
    constructor, client = fake_sdk(monkeypatch)
    response = storage[0].post("/leads/qualify-ai", json=WARM)
    assert response.status_code == 200
    body = response.json()
    assert body["ai_status"] == "success"
    assert body["deterministic"]["lead_score"] == score_lead(LeadCreate(**WARM)).lead_score
    assert body["final_qualification"] == "hot"
    kwargs = client.responses.parse.call_args.kwargs
    payload = json.loads(kwargs["input"])
    assert set(payload) == {"company", "message", "source", "service_interest", "budget_range", "timeline", "company_size"}
    assert BASE["name"] not in kwargs["input"] and BASE["email"] not in kwargs["input"]
    assert kwargs["text_format"] is AILeadAssessment and kwargs["store"] is False
    assert constructor.call_args.kwargs["timeout"] == 15
    assert constructor.call_args.kwargs["max_retries"] == 0
    assert storage[0].get("/leads").json() == []


@pytest.mark.parametrize("payload", [
    STRONG | {"lead_score": 100}, STRONG | {"intent_strength": "invalid"},
    STRONG | {"summary": " "}, STRONG | {"summary": "x" * 501},
    STRONG | {"risk_flags": ["risk"] * 9}, STRONG | {"key_signals": ["x" * 161]},
    {}, None,
])
def test_invalid_output_falls_back(monkeypatch, payload):
    fake_sdk(monkeypatch, payload=payload)
    result = TestClient(app).post("/leads/qualify-ai", json=BASE)
    assert result.status_code == 200
    assert result.json()["ai_status"] == "fallback"
    assert result.json()["ai_assessment"] is None
    assert result.json()["final_qualification"] == "cold"


@pytest.mark.parametrize("error", [TimeoutError("private provider error"), RuntimeError("private provider error")])
def test_sdk_failure_fallback(monkeypatch, error):
    fake_sdk(monkeypatch, error=error)
    response = TestClient(app).post("/leads/qualify-ai", json=BASE)
    assert response.status_code == 200 and response.json()["ai_status"] == "fallback"
    assert "private provider error" not in response.text


def test_missing_key_fallback():
    response = TestClient(app).post("/leads/qualify-ai", json=BASE)
    assert response.status_code == 200
    result = response.json()
    assert result["ai_status"] == "fallback"
    assert result["deterministic"] == score_lead(LeadCreate(**BASE)).model_dump(mode="json")


def test_incomplete_response_fallback(monkeypatch):
    fake_sdk(monkeypatch, status="incomplete")
    assert ai.qualify_with_ai(LeadCreate(**BASE)).ai_status == "fallback"


@pytest.mark.parametrize("success", [True, False])
def test_capture_ai_and_duplicate_skip(monkeypatch, storage, success):
    _, sdk = fake_sdk(monkeypatch, payload=STRONG if success else None)
    client = storage[0]
    response = client.post("/leads?use_ai=true", json=WARM)
    assert response.status_code == 201
    stored = response.json()["lead"]
    assert stored["ai_status"] == ("success" if success else "fallback")
    assert stored["lead_score"] == 47 and stored["qualification"] == "warm"
    assert stored["final_qualification"] == ("hot" if success else "warm")
    assert (stored["ai_assessment"] is not None) == success
    assert "dedup_key" not in stored
    assert client.get(f"/leads/{stored['id']}").json() == stored
    assert client.get("/leads").json() == [stored]
    duplicate = client.post("/leads?use_ai=true", json=WARM | {"message": "A different inquiry message."})
    assert duplicate.status_code == 200 and duplicate.json() == {"created": False, "lead": stored}
    assert sdk.responses.parse.call_count == 1


def test_default_capture_never_calls_ai(monkeypatch, storage):
    _, sdk = fake_sdk(monkeypatch)
    client = storage[0]
    stored = client.post("/leads", json=BASE).json()["lead"]
    assert stored["ai_status"] is None and stored["ai_assessment"] is None
    assert stored["final_qualification"] == stored["qualification"]
    assert client.post("/leads?use_ai=true", json=BASE).status_code == 200
    sdk.responses.parse.assert_not_called()


def test_legacy_response_defaults(storage):
    lead = storage[0].post("/leads", json=BASE).json()["lead"]
    for field in ["ai_status", "ai_assessment", "final_qualification", "final_priority", "final_recommended_action"]:
        lead.pop(field)
    restored = LeadStored.model_validate(lead)
    assert restored.final_qualification == restored.qualification


def test_old_database_rejected_without_data_loss(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE leads (id TEXT PRIMARY KEY)"))
        conn.execute(text("INSERT INTO leads VALUES ('demo')"))
    monkeypatch.setattr("app.api.engine", engine)
    with pytest.raises(RuntimeError, match="schema is outdated"):
        with TestClient(app):
            pass
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM leads")).scalar() == 1
    assert len(inspect(engine).get_columns("leads")) == 1
    engine.dispose()


@pytest.mark.parametrize("case", ["success", "malformed", "refusal", "timeout", "auth", "rate", "service"])
def test_real_sdk_with_in_memory_transport(monkeypatch, case):
    import httpx2
    from openai import OpenAI

    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert body["text"]["format"]["type"] == "json_schema"
        assert body["text"]["format"]["strict"] is True
        assert body["text"]["format"]["schema"]["additionalProperties"] is False
        assert "lead_score" not in body["text"]["format"]["schema"]["properties"]
        if case == "timeout":
            raise httpx2.ReadTimeout("private diagnostic", request=request)
        if case in {"auth", "rate", "service"}:
            return httpx2.Response({"auth": 401, "rate": 429, "service": 500}[case],
                                   json={"error": {"message": "private diagnostic"}})
        content = ({"type": "refusal", "refusal": "Cannot assess."} if case == "refusal" else
                   {"type": "output_text", "text": "not json" if case == "malformed" else json.dumps(STRONG), "annotations": []})
        return httpx2.Response(200, json={
            "id": "response-test", "object": "response", "created_at": 0,
            "model": "gpt-4.1-mini", "status": "completed",
            "output": [{"id": "message-test", "type": "message", "role": "assistant",
                        "status": "completed", "content": [content]}],
        })

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setattr(ai, "OpenAI", lambda **kwargs: OpenAI(
        **kwargs, http_client=httpx2.Client(transport=httpx2.MockTransport(handler))))
    response = TestClient(app).post("/leads/qualify-ai", json=BASE)
    assert response.status_code == 200
    assert response.json()["ai_status"] == ("success" if case == "success" else "fallback")
    assert "private diagnostic" not in response.text
    assert len(requests) == 1
