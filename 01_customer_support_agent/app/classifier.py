from openai import OpenAI

from app.config import OPENAI_API_KEY
from app.models import SupportClassification


client = OpenAI(api_key=OPENAI_API_KEY)


def classify_customer_message(
    customer_message: str,
) -> SupportClassification:
    if not customer_message.strip():
        raise ValueError("Customer message cannot be empty.")

    response = client.responses.parse(
        model="gpt-5.5",
        instructions=(
            "You are a professional e-commerce customer support "
            "classification agent. "
            "Analyze the customer's message accurately. "
            "Use high priority for complaints, damaged items, "
            "payment problems, serious delivery problems, or urgent issues. "
            "Set requires_human to true when human review, manual action, "
            "dispute handling, replacement approval, or refund approval "
            "is required. "
            "Write customer_request as a short and clear summary."
        ),
        input=customer_message,
        text_format=SupportClassification,
    )

    if response.output_parsed is None:
        raise RuntimeError(
            "The AI response could not be parsed into the expected format."
        )

    return response.output_parsed