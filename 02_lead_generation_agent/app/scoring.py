"""Pure, transparent preliminary scoring; no network or storage access."""

import re

from app.models import (
    BudgetRange, CompanySize, LeadCreate, LeadQualification, Priority,
    Qualification, RecommendedAction, ScoreBreakdown, ServiceInterest, Timeline,
)

BUDGET_POINTS = {
    BudgetRange.UNKNOWN: 5, BudgetRange.UNDER_500: 6,
    BudgetRange.B500_1000: 12, BudgetRange.B1000_3000: 18,
    BudgetRange.B3000_5000: 22, BudgetRange.B5000_PLUS: 25,
}
TIMELINE_POINTS = {
    Timeline.UNKNOWN: 5, Timeline.IMMEDIATE: 25, Timeline.WITHIN_1_MONTH: 22,
    Timeline.WITHIN_3_MONTHS: 17, Timeline.WITHIN_6_MONTHS: 10,
    Timeline.EXPLORING: 5,
}
COMPANY_POINTS = {
    CompanySize.UNKNOWN: 5, CompanySize.SOLO: 5, CompanySize.S2_10: 8,
    CompanySize.S11_50: 11, CompanySize.S51_200: 13, CompanySize.S200_PLUS: 15,
}
INTENT_TERMS = (
    "price", "pricing", "quote", "cost", "budget", "demo", "consultation",
    "implement", "implementation", "automate", "automation", "integrate",
    "integration", "need", "looking for", "interested", "start", "project",
)


def score_lead(lead: LeadCreate) -> LeadQualification:
    """Score supplied commercial bands and simple English buying-intent signals."""
    service = 5 if lead.service_interest is None else (
        10 if lead.service_interest == ServiceInterest.OTHER else 20
    )
    normalized_message = " ".join(lead.message.casefold().split())
    matches = sum(
        bool(re.search(r"\b" + re.escape(term) + r"\b", normalized_message))
        for term in INTENT_TERMS
    )
    # Distinct terms prevent repetition alone from increasing the score.
    intent = min(matches * 3, 12)
    detail = 3 if len(lead.message) >= 80 else 0
    breakdown = ScoreBreakdown(
        service_interest=service,
        budget=BUDGET_POINTS.get(lead.budget_range, 5),
        timeline=TIMELINE_POINTS.get(lead.timeline, 5),
        company_size=COMPANY_POINTS.get(lead.company_size, 5),
        message_quality=intent + detail,
    )
    total = sum(breakdown.model_dump().values())
    if total >= 70:
        qualification, priority, action = Qualification.HOT, Priority.HIGH, RecommendedAction.CONTACT
    elif total >= 40:
        qualification, priority, action = Qualification.WARM, Priority.MEDIUM, RecommendedAction.REVIEW
    else:
        qualification, priority, action = Qualification.COLD, Priority.LOW, RecommendedAction.NURTURE
    return LeadQualification(
        lead_score=total, qualification=qualification, priority=priority,
        recommended_action=action, score_breakdown=breakdown,
        reasons=[
            f"Service interest: {lead.service_interest or 'missing'} ({service}/20).",
            f"Budget: {lead.budget_range or 'missing'} ({breakdown.budget}/25).",
            f"Timeline: {lead.timeline or 'missing'} ({breakdown.timeline}/25).",
            f"Company size: {lead.company_size or 'missing'} ({breakdown.company_size}/15).",
            f"Message: {matches} distinct intent terms ({intent}/12); detail length bonus ({detail}/3).",
        ],
    )
