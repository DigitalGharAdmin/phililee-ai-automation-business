from app.classifier import classify_customer_message


def main() -> None:
    customer_message = "Where is my order?"

    try:
        result = classify_customer_message(customer_message)

        print("\n--- Customer Support Classification ---")
        print(f"Intent: {result.intent.value}")
        print(f"Priority: {result.priority.value}")
        print(f"Requires human: {result.requires_human}")
        print(f"Customer request: {result.customer_request}")

    except ValueError as exc:
        print(f"\nInvalid customer message: {exc}")

    except RuntimeError as exc:
        print(f"\nAI service error: {exc}")


if __name__ == "__main__":
    main()