import pytest


@pytest.fixture(autouse=True)
def block_real_openai(monkeypatch):
    from app import ai_qualification, settings

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    def blocked(*args, **kwargs):
        raise AssertionError("Real OpenAI clients are forbidden in automated tests")

    monkeypatch.setattr(ai_qualification, "OpenAI", blocked)
