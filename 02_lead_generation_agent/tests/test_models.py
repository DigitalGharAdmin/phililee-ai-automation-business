import pytest
from pydantic import ValidationError

from app.models import LeadCreate

BASE = dict(name="Demo Buyer", email="buyer@example.com", message="Please tell me more.", source="form")


@pytest.mark.parametrize("field,value", [
    ("name", "   "), ("name", "A"), ("name", "a" * 121),
    ("email", "invalid"), ("message", "   "), ("message", "short"),
    ("message", "a" * 5001), ("source", "unknown"),
    ("service_interest", "invalid"), ("budget_range", "invalid"),
    ("timeline", "invalid"), ("company_size", "invalid"),
    ("company", "a" * 201), ("name", 123), ("unexpected", "value"),
])
def test_invalid_input(field, value):
    with pytest.raises(ValidationError):
        LeadCreate(**(BASE | {field: value}))


def test_whitespace_and_email_normalization():
    lead = LeadCreate(**(BASE | dict(name="  Demo Buyer  ", email=" Buyer@EXAMPLE.COM ",
                                     company=" Example Store ", message="  Please tell me more.  ")))
    assert lead.name == "Demo Buyer"
    assert lead.email == "Buyer@example.com"
    assert lead.company == "Example Store"
    assert lead.message == "Please tell me more."


def test_optional_fields_and_blank_company():
    lead = LeadCreate(**BASE, company="   ")
    assert lead.company is None
    assert all(getattr(lead, f) is None for f in ["service_interest", "budget_range", "timeline", "company_size"])


@pytest.mark.parametrize("field", ["name", "email", "message", "source"])
def test_required_fields(field):
    data = BASE.copy()
    del data[field]
    with pytest.raises(ValidationError):
        LeadCreate(**data)
