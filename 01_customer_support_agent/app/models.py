from enum import Enum

from pydantic import BaseModel


class Intent(str, Enum):
    PRODUCT_QUESTION = "product_question"
    ORDER_STATUS = "order_status"
    DELIVERY = "delivery"
    RETURN = "return"
    REFUND = "refund"
    COMPLAINT = "complaint"
    GENERAL = "general"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SupportClassification(BaseModel):
    intent: Intent
    priority: Priority
    requires_human: bool
    customer_request: str