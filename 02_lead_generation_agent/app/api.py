"""Local API for deterministic lead qualification."""

from contextlib import asynccontextmanager
from hashlib import sha256

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import LeadCaptureResponse, LeadCreate, LeadQualification, LeadStored
from app.database import Base, engine, get_db
from app.db_models import Lead
from app.scoring import score_lead
from app.settings import APP_TITLE, APP_VERSION

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Database operation failed."})


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": APP_TITLE, "version": APP_VERSION}


@app.post("/leads/qualify", response_model=LeadQualification)
def qualify(lead: LeadCreate) -> LeadQualification:
    return score_lead(lead)


@app.post("/leads", response_model=LeadCaptureResponse, status_code=201,
          responses={200: {"model": LeadCaptureResponse, "description": "Existing lead"}})
def capture(lead: LeadCreate, response: Response, db: Session = Depends(get_db)):
    qualification = score_lead(lead)
    email = str(lead.email).strip().lower()
    key = sha256(f"{email}|{lead.service_interest or 'unspecified'}".encode("utf-8")).hexdigest()
    query = select(Lead).where(Lead.dedup_key == key)
    existing = db.scalar(query)
    if existing is not None:
        response.status_code = 200
        return LeadCaptureResponse(created=False, lead=LeadStored.model_validate(existing))
    row = Lead(
        **(lead.model_dump(mode="json") | {"email": email}),
        **qualification.model_dump(mode="json", exclude={"score_breakdown", "reasons"}),
        dedup_key=key,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(query)
        if existing is None:
            # An unrelated integrity failure must not masquerade as a duplicate.
            raise
        response.status_code = 200
        return LeadCaptureResponse(created=False, lead=LeadStored.model_validate(existing))
    return LeadCaptureResponse(created=True, lead=LeadStored.model_validate(row))


@app.get("/leads", response_model=list[LeadStored])
def list_leads(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db)):
    return db.scalars(select(Lead).order_by(Lead.created_at.desc(), Lead.id).limit(limit)).all()


@app.get("/leads/{lead_id}", response_model=LeadStored)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    row = db.get(Lead, lead_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return row
