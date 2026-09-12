from itertools import product

import pytest

from app.models import BudgetRange, CompanySize, LeadCreate, ServiceInterest, Timeline
from app.scoring import score_lead
from tests.test_models import BASE


@pytest.mark.parametrize("fields,score,labels", [
    ({}, 20, ("cold", "low", "nurture")),
    (dict(service_interest="other", budget_range="500_1000", timeline="within_3_months", company_size="2_10"),
     47, ("warm", "medium", "review")),
    (dict(service_interest="lead_generation", budget_range="5000_plus", timeline="immediate", company_size="200_plus",
          message="We need a quote for an automation project. Please explain the implementation options for our sales team."),
     100, ("hot", "high", "contact")),
    (dict(service_interest="other", budget_range="500_1000", timeline="within_3_months", company_size=None),
     44, ("warm", "medium", "review")),
])
def test_representative_leads(fields, score, labels):
    result = score_lead(LeadCreate(**(BASE | fields)))
    assert result.lead_score == score
    assert (result.qualification, result.priority, result.recommended_action) == labels
    assert sum(result.score_breakdown.model_dump().values()) == score
    assert len(result.reasons) == 5


@pytest.mark.parametrize("budget,timeline,size,service,total,label", [
    ("500_1000", "within_3_months", "solo", None, 39, "cold"),
    ("unknown", "unknown", "51_200", "other", 33, "cold"),
    ("unknown", "unknown", "200_plus", "lead_generation", 45, "warm"),
    ("3000_5000", "within_3_months", "solo", "lead_generation", 64, "warm"),
])
def test_band_scores(budget, timeline, size, service, total, label):
    result = score_lead(LeadCreate(**BASE, budget_range=budget, timeline=timeline, company_size=size, service_interest=service))
    assert result.lead_score == total
    assert result.qualification == label


@pytest.mark.parametrize("fields,total,label", [
    (dict(service_interest="other", budget_range="unknown", timeline="immediate"), 45, "warm"),
    (dict(service_interest="lead_generation", budget_range="unknown", timeline="within_6_months"), 40, "warm"),
    (dict(service_interest="lead_generation", budget_range="3000_5000", timeline="within_1_month", company_size="solo"), 69, "warm"),
    (dict(service_interest="lead_generation", budget_range="5000_plus", timeline="immediate"), 75, "hot"),
    (dict(service_interest="other", budget_range="5000_plus", timeline="immediate", company_size="solo", message="Please send a quote and demo."), 71, "hot"),
    (dict(service_interest="lead_generation", budget_range="5000_plus", timeline="within_6_months", company_size="200_plus"), 70, "hot"),
])
def test_threshold_boundaries(fields, total, label):
    result = score_lead(LeadCreate(**(BASE | fields)))
    assert result.lead_score == total
    assert result.qualification == label


@pytest.mark.parametrize("message,points", [
    ("Please tell me more.", 0), ("quote quote quote", 3),
    ("NEED a QUOTE for AUTOMATION and a DEMO", 12),
    ("The quotation and needless restarts.", 0),
    ("I am looking   for assistance.", 3),
    ("x" * 79, 0), ("x" * 80, 3),
    ("quote demo budget project " + "x" * 80, 15),
])
def test_message_intent_and_detail(message, points):
    result = score_lead(LeadCreate(**(BASE | {"message": message})))
    assert result.score_breakdown.message_quality == points


def test_all_commercial_combinations_stay_in_range_and_sum_correctly():
    for service, budget, timeline, size in product(
        [None, *ServiceInterest], [None, *BudgetRange], [None, *Timeline], [None, *CompanySize]
    ):
        lead = LeadCreate(**BASE, service_interest=service, budget_range=budget, timeline=timeline, company_size=size)
        result = score_lead(lead)
        assert 0 <= result.lead_score <= 100
        assert sum(result.score_breakdown.model_dump().values()) == result.lead_score


@pytest.mark.parametrize("field,category,bands", [
    ("budget_range", "budget", {"unknown": 5, "under_500": 6, "500_1000": 12, "1000_3000": 18, "3000_5000": 22, "5000_plus": 25}),
    ("timeline", "timeline", {"unknown": 5, "immediate": 25, "within_1_month": 22, "within_3_months": 17, "within_6_months": 10, "exploring": 5}),
    ("company_size", "company_size", {"unknown": 5, "solo": 5, "2_10": 8, "11_50": 11, "51_200": 13, "200_plus": 15}),
])
def test_each_rubric_band(field, category, bands):
    for value, expected in bands.items():
        result = score_lead(LeadCreate(**(BASE | {field: value})))
        assert getattr(result.score_breakdown, category) == expected


def test_scoring_is_repeatable_and_does_not_mutate_input():
    lead = LeadCreate(**BASE)
    before = lead.model_dump()
    assert score_lead(lead) == score_lead(lead)
    assert lead.model_dump() == before
