"""Validated lead input and deterministic qualification response contracts."""

from enum import StrEnum
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class LeadSource(StrEnum):
    WEBSITE = "website"
    FORM = "form"
    EMAIL = "email"
    REFERRAL = "referral"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    GOOGLE_ADS = "google_ads"
    OTHER = "other"


class ServiceInterest(StrEnum):
    AI_CUSTOMER_SUPPORT = "ai_customer_support"
    LEAD_GENERATION = "lead_generation"
    EMAIL_AUTOMATION = "email_automation"
    N8N_AUTOMATION = "n8n_automation"
    RAG_KNOWLEDGE_BOT = "rag_knowledge_bot"
    REPORTING_DASHBOARD = "reporting_dashboard"
    CUSTOM_AI_AUTOMATION = "custom_ai_automation"
    OTHER = "other"


class BudgetRange(StrEnum):
    UNKNOWN = "unknown"
    UNDER_500 = "under_500"
    B500_1000 = "500_1000"
    B1000_3000 = "1000_3000"
    B3000_5000 = "3000_5000"
    B5000_PLUS = "5000_plus"


class Timeline(StrEnum):
    UNKNOWN = "unknown"
    IMMEDIATE = "immediate"
    WITHIN_1_MONTH = "within_1_month"
    WITHIN_3_MONTHS = "within_3_months"
    WITHIN_6_MONTHS = "within_6_months"
    EXPLORING = "exploring"


class CompanySize(StrEnum):
    UNKNOWN = "unknown"
    SOLO = "solo"
    S2_10 = "2_10"
    S11_50 = "11_50"
    S51_200 = "51_200"
    S200_PLUS = "200_plus"


class Qualification(StrEnum):
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendedAction(StrEnum):
    NURTURE = "nurture"
    REVIEW = "review"
    CONTACT = "contact"


class LeadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    company: str | None = Field(default=None, max_length=200)
    message: str = Field(min_length=10, max_length=5000)
    source: LeadSource
    service_interest: ServiceInterest | None = None
    budget_range: BudgetRange | None = None
    timeline: Timeline | None = None
    company_size: CompanySize | None = None

    @field_validator("email", mode="before")
    @classmethod
    def trim_email(cls, value: object) -> object:
        # EmailStr normalizes the domain; preserve local-part case.
        return value.strip() if isinstance(value, str) else value

    @field_validator("company")
    @classmethod
    def blank_company_is_missing(cls, value: str | None) -> str | None:
        return value or None


class ScoreBreakdown(BaseModel):
    service_interest: int = Field(ge=0, le=20)
    budget: int = Field(ge=0, le=25)
    timeline: int = Field(ge=0, le=25)
    company_size: int = Field(ge=0, le=15)
    message_quality: int = Field(ge=0, le=15)


class LeadQualification(BaseModel):
    lead_score: int = Field(ge=0, le=100)
    qualification: Qualification
    priority: Priority
    recommended_action: RecommendedAction
    score_breakdown: ScoreBreakdown
    reasons: list[str]


class AILeadAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    intent_strength: Literal["low", "medium", "high"]
    business_fit: Literal["poor", "fair", "good", "excellent"]
    urgency: Literal["low", "medium", "high"]
    decision_readiness: Literal["exploring", "considering", "ready"]
    ai_recommended_action: RecommendedAction
    summary: str = Field(min_length=1, max_length=500)
    key_signals: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(max_length=8)
    risk_flags: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(max_length=8)


class LeadAIQualification(BaseModel):
    deterministic: LeadQualification
    ai_assessment: AILeadAssessment | None
    ai_status: Literal["success", "fallback"]
    final_qualification: Qualification
    final_priority: Priority
    final_recommended_action: RecommendedAction
    final_reasons: list[str]


class LeadStored(LeadCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_score: int = Field(ge=0, le=100)
    qualification: Qualification
    priority: Priority
    recommended_action: RecommendedAction
    created_at: datetime
    updated_at: datetime
    ai_status: Literal["success", "fallback"] | None = None
    ai_assessment: AILeadAssessment | None = None
    final_qualification: Qualification | None = None
    final_priority: Priority | None = None
    final_recommended_action: RecommendedAction | None = None

    @model_validator(mode="after")
    def deterministic_defaults(self):
        self.final_qualification = self.final_qualification or self.qualification
        self.final_priority = self.final_priority or self.priority
        self.final_recommended_action = self.final_recommended_action or self.recommended_action
        return self

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        # SQLite drops timezone information; all stored timestamps originate in UTC.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class LeadCaptureResponse(BaseModel):
    created: bool
    lead: LeadStored
