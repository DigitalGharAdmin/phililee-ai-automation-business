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

    except Exception as exc:
        print(f"\nClassification failed: {exc}")


if __name__ == "__main__":
    main()