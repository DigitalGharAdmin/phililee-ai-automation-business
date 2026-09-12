"""Local API for deterministic lead qualification."""

from fastapi import FastAPI

from app.models import LeadCreate, LeadQualification
from app.scoring import score_lead
from app.settings import APP_TITLE, APP_VERSION

app = FastAPI(title=APP_TITLE, version=APP_VERSION)


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": APP_TITLE, "version": APP_VERSION}


@app.post("/leads/qualify", response_model=LeadQualification)
def qualify(lead: LeadCreate) -> LeadQualification:
    return score_lead(lead)
