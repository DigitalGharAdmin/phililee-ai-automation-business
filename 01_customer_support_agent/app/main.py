import os
from enum import Enum

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


# Load environment variables from .env
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is missing. Add it to the .env file."
    )

client = OpenAI(api_key=api_key)


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


def classify_customer_message(
    customer_message: str,
) -> SupportClassification:
    response = client.responses.parse(
        model="gpt-5.5",
        instructions=(
            "You are a professional e-commerce customer support "
            "classification agent. "
            "Analyze the customer's message accurately. "
            "Use high priority for complaints, damaged items, "
            "payment problems, serious delivery problems, or situations "
            "requiring urgent support. "
            "Set requires_human to true when the issue requires human "
            "review, escalation, manual action, dispute handling, "
            "replacement approval, refund approval, or information "
            "that the AI cannot safely resolve by itself. "
            "Write customer_request as a short, clear summary of what "
            "the customer wants."
        ),
        input=customer_message,
        text_format=SupportClassification,
    )

    if response.output_parsed is None:
        raise RuntimeError(
            "The AI response could not be parsed into the expected format."
        )

    return response.output_parsed


if __name__ == "__main__":
    customer_message = (
        "My product arrived broken and I want replacement."
    )

    try:
        result = classify_customer_message(customer_message)

        print("\n--- Customer Support Classification ---")
        print(f"Intent: {result.intent.value}")
        print(f"Priority: {result.priority.value}")
        print(f"Requires human: {result.requires_human}")
        print(f"Customer request: {result.customer_request}")

    except Exception as exc:
        print(f"\nCustomer support classification failed: {exc}")