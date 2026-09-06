import re
import anyio

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import require_n8n_support_service
from app.customer_auth import require_firebase_customer
from app.authorization import get_customer_owned_order, require_permissions
from app.database import get_db
from app.order_store import INITIAL_ORDERS, build_order_query, list_orders, reset_orders
from app.principals import AuthenticatedPrincipal, Permission
from app.settings import SETTINGS, debug_endpoints_enabled
from app.security import SecurityMiddleware, build_external_limiter, enforce_shared_principal_rate_limit
from sqlalchemy import text

app = FastAPI(
    title="Customer Support AI Agent API",
    version="2.1.0",
    description="Customer support backend for tracking, cancellation, return and refund."
)
EXTERNAL_RATE_LIMITER = build_external_limiter(SETTINGS)
app.add_middleware(SecurityMiddleware, settings_getter=lambda: SETTINGS, external_limiter=EXTERNAL_RATE_LIMITER)


async def require_rate_limited_service(
    principal: AuthenticatedPrincipal = Depends(require_n8n_support_service),
):
    await enforce_shared_principal_rate_limit(principal, "/support", SETTINGS, EXTERNAL_RATE_LIMITER)
    return principal


async def require_rate_limited_customer(
    principal: AuthenticatedPrincipal = Depends(require_firebase_customer),
):
    await enforce_shared_principal_rate_limit(principal, "/v2/support", SETTINGS, EXTERNAL_RATE_LIMITER)
    return principal


@app.middleware("http")
async def protect_debug_endpoints(request: Request, call_next):
    if request.url.path.startswith("/debug/") and not debug_endpoints_enabled():
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    return await call_next(request)

ORDER_NUMBER_TOKEN_PATTERN = re.compile(
    r"(?<![A-Z0-9])DG-\d{4}(?![A-Z0-9])",
    re.IGNORECASE,
)

def validate_order_number(order_number: str) -> tuple[bool, str | None]:
    """
    Valid order format example: DG-1001
    Rules:
    - Must start with DG-
    - Must end with exactly 4 digits
    """
    if order_number is None:
        return False, "Order number is required."

    order_number = order_number.strip().upper()

    if not order_number:
        return False, "Order number is required."

    if not re.fullmatch(r"DG-\d{4}", order_number):
        return (
            False,
            "Invalid order number format. Please use the format DG-1234, for example DG-1001.",
        )

    return True, None

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    if request.url.path == "/v2/support":
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "type": "validation_error",
                "message": "The request data is invalid or incomplete.",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "type": "internal_server_error",
                "message": "Something went wrong while processing your request. Please try again.",
            }
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
):
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "error": {
                "type": "database_error",
                "message": "The service is temporarily unable to access order data.",
            },
        },
    )

class SupportRequest(BaseModel):
    customer_name: str
    order_number: str
    message: str


class CustomerSupportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_number: str
    message: str


# =========================================================
# HELPERS
# =========================================================

def normalize_order_number(order_number: str) -> str:
    normalized_value = order_number.strip().upper()
    order_number_tokens = ORDER_NUMBER_TOKEN_PATTERN.findall(normalized_value)

    if len(order_number_tokens) == 1:
        return order_number_tokens[0].upper()

    return normalized_value


def normalize_message(message: str) -> str:
    return message.strip().lower()


def analyze_intent(message: str) -> tuple[str, str | None]:
    msg = normalize_message(message)

    intent_keywords = {
        "refund_order": [
        "refund",
        "money back",
        "give my money back",
        "want my money back",
        ],
        "return_order": [
            "return",
            "send it back",
            "send item back",
        ],
        "cancel_order": [
            "cancel",
            "cancellation",
        ],
        "track_order": [
            "where is my order",
            "track",
            "tracking",
            "order status",
            "status",
            "delivery",
            "when will",
            "where is",
        ],
    }
    detected = [
        intent
        for intent, keywords in intent_keywords.items()
        if any(keyword in msg for keyword in keywords)
    ]

    if len(detected) > 1:
        return "general_support", "multiple_intents"

    if not detected:
        return "general_support", None

    intent = detected[0]
    if intent == "track_order":
        return intent, None

    action = intent.removesuffix("_order")
    negated_action = re.search(
        rf"\b(?:do not|don't|dont|never)\b.{{0,40}}\b{action}\b"
        rf"|\bnot\s+(?:want|wishing|trying)\s+to\s+{action}\b",
        msg,
    )

    if negated_action:
        return "general_support", "negated_action"

    informational_markers = [
        "can i",
        "could i",
        "may i",
        "am i eligible",
        "what happens if",
        "how do i",
        "is it possible",
    ]
    if any(marker in msg for marker in informational_markers):
        return "general_support", "informational_question"

    return intent, None


def detect_intent(message: str) -> str:
    intent, _ = analyze_intent(message)
    return intent

@app.get("/debug/intent")
def debug_intent(message: str):
    return {
        "message": message,
        "normalized_message": normalize_message(message),
        "intent": detect_intent(message),
    }
# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Customer Support AI Agent API is running",
        "version": "2.1.0",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    def database_ready():
        from app.database import engine
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
    try:
        await anyio.to_thread.run_sync(database_ready)
        if EXTERNAL_RATE_LIMITER is not None and not await EXTERNAL_RATE_LIMITER.ready():
            raise RuntimeError("limiter unavailable")
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready"}


# =========================================================
# DEBUG: VIEW CURRENT STATE
# =========================================================

@app.get("/debug/orders")
def debug_orders(db: Session = Depends(get_db)):
    return list_orders(db)


# =========================================================
# DEBUG: RESET ALL DEMO ORDERS
# =========================================================

@app.post("/debug/reset")
def reset_demo_orders(db: Session = Depends(get_db)):
    restored_orders = reset_orders(db)
    db.commit()

    return {
        "success": True,
        "message": "Demo orders reset successfully.",
        "orders": restored_orders,
    }

# =========================================================
# SUPPORT ENDPOINT
# =========================================================

@app.post("/support")
def customer_support(
    request: SupportRequest,
    db: Session = Depends(get_db),
    _principal: AuthenticatedPrincipal = Depends(require_rate_limited_service),
):

    customer_name = request.customer_name.strip()
    order_number = normalize_order_number(request.order_number)
    message = request.message.strip()

    if not customer_name:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "type": "invalid_customer_name",
                    "message": "Customer name is required.",
                },
                "customer_name": customer_name,
                "order_number": order_number,
                "message": message,
            },
        )

    if not message:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "type": "invalid_message",
                    "message": "Message is required.",
                },
                "customer_name": customer_name,
                "order_number": order_number,
                "message": message,
            },
        )

    intent, intent_safety_reason = analyze_intent(message)

    is_valid_order_number, order_number_error = validate_order_number(order_number)

    if not is_valid_order_number:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "type": "invalid_order_number",
                    "message": order_number_error,
                },
                "customer_name": customer_name,
                "order_number": order_number,
                "message": message,
            },
        )

    state_changing_intents = {"cancel_order", "return_order", "refund_order"}
    order = db.scalar(
        build_order_query(
            order_number,
            for_update=intent in state_changing_intents,
        )
    )

    if order is None:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "type": "order_not_found",
                    "message": f"Order {order_number} was not found.",
                },
                "intent": intent,
                "customer_name": customer_name,
                "order_number": order_number,
                "message": message,
                "response": (
                    f"I couldn't find order {order_number}. "
                    "Please double-check the order number and try again."
                ),
            },
        )

    stored_customer_name = order["customer_name"]

    if customer_name.casefold() != stored_customer_name.strip().casefold():
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": {
                    "type": "customer_order_mismatch",
                    "message": "The customer name does not match this order.",
                },
                "customer_name": customer_name,
                "order_number": order_number,
                "message": message,
            },
        )

    return execute_support_operation(
        db, order, order_number, message, intent, intent_safety_reason
    )


@app.post("/v2/support")
def firebase_customer_support(
    request: CustomerSupportRequest,
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_rate_limited_customer),
):
    require_permissions(principal, {Permission.CUSTOMER_ORDER_ACCESS})
    order_number = request.order_number.strip().upper()
    message = request.message.strip()
    valid, error = validate_order_number(order_number)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")
    intent, safety_reason = analyze_intent(message)
    # This scoped query both authorizes and locks the current row before mutation.
    order = get_customer_owned_order(
        db, principal=principal, order_number=order_number,
        for_update=intent in {"cancel_order", "return_order", "refund_order"},
    )
    result = execute_support_operation(db, order, order_number, message, intent, safety_reason)
    result.pop("customer_name", None)
    return result


def execute_support_operation(db, order, order_number, message, intent, intent_safety_reason):
    """Apply the shared rules to an order authorized by the calling route."""
    stored_customer_name = order["customer_name"]
    if intent_safety_reason:
        if intent_safety_reason == "multiple_intents":
            response = (
                "I found more than one requested action. Please choose one: "
                "tracking, cancellation, return, or refund. No changes were made."
            )
        elif intent_safety_reason == "negated_action":
            response = "No changes were made to your order."
        else:
            response = (
                "I can explain the available options, but no changes were made. "
                "Please make an explicit request if you want to proceed."
            )

        return {
            "success": True,
            "intent": "general_support",
            "customer_name": stored_customer_name,
            "order_number": order_number,
            "status": order["status"],
            "message": message,
            "response": response,
        }

    # =====================================================
    # TRACK ORDER
    # =====================================================

    if intent == "track_order":
        is_cancelled = order["status"] == "Cancelled"
        tracking_result = {
            "success": True,
            "intent": "track_order",
            "customer_name": stored_customer_name,
            "order_number": order_number,
            "status": order["status"],
            "estimated_delivery": None if is_cancelled else order["estimated_delivery"],
            "tracking_number": None if is_cancelled else order["tracking_number"],
            "message": message,
        }

        delivered_on = order.get("delivered_on")
        if is_cancelled:
            status_detail = f"Order {order_number} is currently Cancelled."
            delivery_detail = None
        elif delivered_on:
            tracking_result["delivered_on"] = delivered_on
            status_detail = f"Order {order_number} is currently: {order['status']}."
            delivery_detail = f"Delivered on: {delivered_on}."
        else:
            status_detail = f"Order {order_number} is currently {order['status']}."
            delivery_detail = f"Estimated delivery: {order['estimated_delivery']}."

        workflow_details = []
        if order.get("return_id"):
            tracking_result["return_id"] = order["return_id"]
            workflow_details.append(f"Return ID: {order['return_id']}.")
        if order.get("refund_id"):
            tracking_result["refund_id"] = order["refund_id"]
            workflow_details.append(f"Refund ID: {order['refund_id']}.")

        response_parts = [
            status_detail,
            delivery_detail,
            *workflow_details,
            None if is_cancelled else f"Tracking number: {order['tracking_number']}.",
        ]
        tracking_result["response"] = " ".join(
            part for part in response_parts if part is not None
        )

        return tracking_result

    # =====================================================
    # CANCEL ORDER
    # =====================================================

    if intent == "cancel_order":

        status = order["status"]

        # Already cancelled
        if status == "Cancelled":
            return {
                "success": False,
                "intent": "cancel_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "cancelled": False,
                "message": message,
                "response": f"Order {order_number} has already been cancelled.",
            }

        # Delivered orders cannot be cancelled
        if status == "Delivered":
            return {
                "success": False,
                "intent": "cancel_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "cancelled": False,
                "message": message,
                "response": (
                    f"Order {order_number} cannot be cancelled because "
                    "it has already been delivered."
                ),
            }

        # Out for delivery orders cannot be cancelled
        if status == "Out for Delivery":
            return {
                "success": False,
                "intent": "cancel_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "cancelled": False,
                "message": message,
                "response": (
                    f"Order {order_number} cannot be cancelled because "
                    "its current status is Out for Delivery."
                ),
            }

        # Refund request takes priority when current status is Refund Requested
        if status == "Refund Requested":
            return {
                "success": False,
                "intent": "cancel_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "cancelled": False,
                "message": message,
                "response": (
                    f"Order {order_number} cannot be cancelled because "
                    "a refund request has already been submitted."
                ),
            }

        # Return request
        if status == "Return Requested":
            return {
                "success": False,
                "intent": "cancel_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "cancelled": False,
                "message": message,
                "response": (
                    f"Order {order_number} cannot be cancelled because "
                    "a return request has already been submitted."
                ),
            }

        # Fallback flag checks
        if order.get("refund_requested") is True:
            return {
                "success": False,
                "intent": "cancel_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "cancelled": False,
                "message": message,
                "response": (
                    f"Order {order_number} cannot be cancelled because "
                    "a refund request has already been submitted."
                ),
            }

        if order.get("return_requested") is True:
            return {
                "success": False,
                "intent": "cancel_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "cancelled": False,
                "message": message,
                "response": (
                    f"Order {order_number} cannot be cancelled because "
                    "a return request has already been submitted."
                ),
            }

        # Completed refund
        if status == "Refunded":
            return {
                "success": False,
                "intent": "cancel_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "cancelled": False,
                "message": message,
                "response": (
                    f"Order {order_number} cannot be cancelled because "
                    "the order has already been refunded."
                ),
            }

        # Cancellation is allowed only while Processing
        if status != "Processing":
            return {
                "success": False,
                "intent": "cancel_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "cancelled": False,
                "message": message,
                "response": (
                    f"Order {order_number} cannot be cancelled from its "
                    f"current status: {status}."
                ),
            }

        order["status"] = "Cancelled"
        db.commit()

        return {
            "success": True,
            "intent": "cancel_order",
            "customer_name": stored_customer_name,
            "order_number": order_number,
            "status": order["status"],
            "cancelled": True,
            "message": message,
            "response": f"Order {order_number} has been cancelled successfully.",
        }

    # RETURN ORDER
    # =====================================================

    if intent == "return_order":

        status = order["status"]

        # Refund workflow has already started
        if status == "Refund Requested" or order.get("refund_requested") is True:
            return {
                "success": False,
                "intent": "return_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "return_requested": order.get("return_requested", False),
                "refund_requested": True,
                "message": message,
                "response": (
                    f"Order {order_number} already has a refund request in progress. "
                    "A new return request cannot be submitted."
                ),
            }

        # Return already requested
        if status == "Return Requested" or order.get("return_requested") is True:
            return {
                "success": False,
                "intent": "return_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "return_requested": True,
                "message": message,
                "response": (
                    f"A return request has already been submitted "
                    f"for order {order_number}."
                ),
            }

        # Cancelled orders cannot be returned
        if status == "Cancelled":
            return {
                "success": False,
                "intent": "return_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "return_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} was cancelled and is not eligible "
                    "for a return request."
                ),
            }

        # Processing orders cannot be returned
        if status == "Processing":
            return {
                "success": False,
                "intent": "return_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "return_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} has not been delivered yet, "
                    "so a return cannot be requested."
                ),
            }

        # Out-for-delivery orders cannot be returned yet
        if status == "Out for Delivery":
            return {
                "success": False,
                "intent": "return_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "return_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} is still Out for Delivery. "
                    "A return can be requested after delivery."
                ),
            }

        # Return is allowed only after delivery
        if status != "Delivered":
            return {
                "success": False,
                "intent": "return_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "return_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} cannot be returned from its "
                    f"current status: {status}."
                ),
            }

        order["return_requested"] = True
        order["status"] = "Return Requested"
        order["return_id"] = f"RET-{order_number.replace('DG-', '')}"
        db.commit()

        return {
            "success": True,
            "intent": "return_order",
            "customer_name": stored_customer_name,
            "order_number": order_number,
            "status": order["status"],
            "return_requested": True,
            "return_id": order["return_id"],
            "message": message,
            "response": (
                f"Your return request for order {order_number} "
                f"has been submitted successfully. "
                f"Return ID: RET-{order_number.replace('DG-', '')}."
            ),
        }

    # REFUND ORDER
    # =====================================================

    if intent == "refund_order":

        status = order["status"]

        # -------------------------------------------------
        # 1. Refund already requested
        # -------------------------------------------------
        if status == "Refund Requested" or order.get("refund_requested") is True:
            return {
                "success": False,
                "intent": "refund_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "refund_requested": True,
                "message": message,
                "response": (
                    f"A refund request has already been submitted "
                    f"for order {order_number}."
                ),
            }

        # -------------------------------------------------
        # 2. Return already requested
        #    Return and refund cannot run at the same time
        # -------------------------------------------------
        if status == "Return Requested" or order.get("return_requested") is True:
            return {
                "success": False,
                "intent": "refund_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "refund_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} already has a return request in progress. "
                    "A new refund request cannot be submitted."
                ),
            }

        # -------------------------------------------------
        # 3. Processing orders are not eligible
        # -------------------------------------------------
        if status == "Processing":
            return {
                "success": False,
                "intent": "refund_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "refund_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} is not currently eligible for a refund."
                ),
            }

        # -------------------------------------------------
        # 4. Out for Delivery orders are not eligible
        # -------------------------------------------------
        if status == "Out for Delivery":
            return {
                "success": False,
                "intent": "refund_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "refund_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} is still Out for Delivery "
                    "and is not currently eligible for a refund."
                ),
            }

        # -------------------------------------------------
        # 5. Cancelled orders cannot use refund workflow
        # -------------------------------------------------
        if status == "Cancelled":
            return {
                "success": False,
                "intent": "refund_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "refund_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} is cancelled and cannot use "
                    "this refund workflow."
                ),
            }

        # -------------------------------------------------
        # 6. Already refunded
        # -------------------------------------------------
        if status == "Refunded":
            return {
                "success": False,
                "intent": "refund_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "refund_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} has already been refunded."
                ),
            }

        # -------------------------------------------------
        # 7. Only Delivered orders reach here
        # -------------------------------------------------
        if status != "Delivered":
            return {
                "success": False,
                "intent": "refund_order",
                "customer_name": stored_customer_name,
                "order_number": order_number,
                "status": status,
                "refund_requested": False,
                "message": message,
                "response": (
                    f"Order {order_number} is not currently eligible for a refund."
                ),
            }

        # -------------------------------------------------
        # 8. Submit refund request
        # -------------------------------------------------
        order["refund_requested"] = True
        order["status"] = "Refund Requested"
        order["refund_id"] = f"REF-{order_number.replace('DG-', '')}"
        db.commit()

        return {
            "success": True,
            "intent": "refund_order",
            "customer_name": stored_customer_name,
            "order_number": order_number,
            "status": order["status"],
            "refund_requested": True,
            "refund_id": order["refund_id"],
            "message": message,
            "response": (
                f"Your refund request for order {order_number} "
                f"has been submitted successfully. "
                f"Refund ID: REF-{order_number.replace('DG-', '')}."
            ),
        }

    # =====================================================
    # GENERAL SUPPORT
    # =====================================================

    return {
        "success": True,
        "intent": "general_support",
        "customer_name": stored_customer_name,
        "order_number": order_number,
        "status": order["status"],
        "message": message,
        "response": (
            f"Order {order_number} was found. "
            "Please tell me whether you need tracking, cancellation, "
            "return, or refund assistance."
        ),
    }
