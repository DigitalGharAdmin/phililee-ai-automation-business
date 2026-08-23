from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.config import OPENAI_API_KEY
from app.logger import get_logger
from app.models import SupportClassification


logger = get_logger("customer_support")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    timeout=20.0,
    max_retries=2,
)


def classify_customer_message(
    customer_message: str,
) -> SupportClassification:
    cleaned_message = customer_message.strip()

    if not cleaned_message:
        raise ValueError("Customer message cannot be empty.")

    logger.info("Starting customer message classification.")

    try:
        response = client.responses.parse(
            model="gpt-5.5",
            instructions=(
                "You are a professional e-commerce customer support "
                "classification agent. "
                "Analyze the customer's message accurately. "
                "Use high priority for complaints, damaged items, "
                "payment problems, serious delivery problems, or urgent issues. "
                "Set requires_human to true when human review, manual action, "
                "dispute handling, replacement approval, refund approval, "
                "or another manual business action is required. "
                "Write customer_request as a short and clear summary."
            ),
            input=cleaned_message,
            text_format=SupportClassification,
        )

    except AuthenticationError as exc:
        logger.error("OpenAI authentication failed.")
        raise RuntimeError(
            "AI service authentication failed."
        ) from exc

    except RateLimitError as exc:
        logger.warning("OpenAI rate limit or quota limit reached.")
        raise RuntimeError(
            "AI service is temporarily unavailable due to usage limits."
        ) from exc

    except APITimeoutError as exc:
        logger.warning("OpenAI request timed out.")
        raise RuntimeError(
            "AI service request timed out."
        ) from exc

    except APIConnectionError as exc:
        logger.error("Could not connect to OpenAI.")
        raise RuntimeError(
            "Could not connect to the AI service."
        ) from exc

    if response.output_parsed is None:
        logger.error("AI response could not be parsed.")
        raise RuntimeError(
            "The AI response could not be parsed into the expected format."
        )

    logger.info("Customer message classified successfully.")

    return response.output_parsed