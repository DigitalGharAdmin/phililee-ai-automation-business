"""Small, dependency-free HTTP hardening for the API surface."""

import hashlib
import json
import logging
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from fastapi import HTTPException

SENSITIVE_KEYS = {"authorization", "token", "password", "api_key", "service_key", "database_url", "digest"}
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
SUPPORT_PATHS = {"/support", "/v2/support"}
DOC_PATHS = {"/docs", "/redoc", "/openapi.json"}
logger = logging.getLogger("app.http")


def redact(value):
    """Redact known credential-bearing fields without rendering their values."""
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.casefold() in SENSITIVE_KEYS else redact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


class MemoryRateLimiter:
    """Bounded-process limiter used locally and as production defense in depth."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self):
        with self._lock:
            self._events.clear()

    def allow(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = self.clock()
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - window:
                events.popleft()
            if len(events) >= limit:
                retry = max(1, int(window - (now - events[0])))
                return False, retry
            events.append(now)
            return True, window


RATE_LIMITER = MemoryRateLimiter()


class RedisRateLimiter:
    """Atomic fixed-window limiter backed by a shared Redis-compatible service."""
    SCRIPT = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; local t=redis.call('TTL',KEYS[1]); return {n,t}"

    def __init__(self, url: str):
        from redis.asyncio import from_url
        self.client = from_url(url, decode_responses=False, socket_connect_timeout=3, socket_timeout=3)

    async def allow(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        count, ttl = await self.client.eval(self.SCRIPT, 1, "support-rate:" + key, window)
        return int(count) <= limit, max(1, int(ttl))

    async def ready(self):
        return bool(await self.client.ping())

    async def close(self):
        await self.client.aclose()


def build_external_limiter(settings):
    return RedisRateLimiter(settings.rate_limit_redis_url) if settings.rate_limit_backend == "external" else None


def enforce_principal_rate_limit(principal, path: str, settings, limiter=RATE_LIMITER):
    """Limit authenticated identities without retaining their identifiers."""
    identity = principal.customer_id if principal.customer_id is not None else principal.subject
    fingerprint = hashlib.sha256(f"{principal.principal_type.value}:{identity}".encode()).hexdigest()
    allowed, retry = limiter.allow("principal:" + path + ":" + fingerprint, settings.rate_limit_requests, settings.rate_limit_window_seconds)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many requests.", headers={"Retry-After": str(retry)})


async def enforce_shared_principal_rate_limit(principal, path: str, settings, external_limiter=None):
    enforce_principal_rate_limit(principal, path, settings)
    if external_limiter is None:
        return
    identity = principal.customer_id if principal.customer_id is not None else principal.subject
    fingerprint = hashlib.sha256(f"{principal.principal_type.value}:{identity}".encode()).hexdigest()
    try:
        allowed, retry = await external_limiter.allow("principal:" + path + ":" + fingerprint, settings.rate_limit_requests, settings.rate_limit_window_seconds)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.") from exc
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many requests.", headers={"Retry-After": str(retry)})


def _response(status: int, detail: str, headers: list[tuple[bytes, bytes]] | None = None):
    body = json.dumps({"detail": detail}, separators=(",", ":")).encode()
    return {
        "type": "http.response.start", "status": status,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), *(headers or [])],
    }, {"type": "http.response.body", "body": body}


def _host_allowed(host: str, allowed: tuple[str, ...]) -> bool:
    return any(rule == "*" or host == rule or (rule.startswith("*.") and host.endswith(rule[1:]) and host != rule[2:]) for rule in allowed)


class SecurityMiddleware:
    def __init__(self, app, settings_getter, external_limiter=None):
        self.app = app
        self.settings_getter = settings_getter
        self.external_limiter = external_limiter

    async def _limit(self, key, limit, window):
        local = RATE_LIMITER.allow(key, limit, window)
        if not local[0] or self.external_limiter is None:
            return local
        try:
            return await self.external_limiter.allow(key, limit, window)
        except Exception:
            return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        settings = self.settings_getter()
        headers = Headers(scope=scope)
        path, method = scope["path"], scope["method"].upper()
        supplied_id = headers.get("x-request-id", "")
        request_id = supplied_id if REQUEST_ID_PATTERN.fullmatch(supplied_id) else uuid.uuid4().hex
        started = time.monotonic()

        host_value = headers.get("host", "")
        try:
            host = urlsplit("//" + host_value).hostname or ""
        except ValueError:
            host = ""
        if not _host_allowed(host.casefold(), settings.trusted_hosts):
            return await self._send_direct(send, 400, "Invalid host.", request_id, settings)
        if path.startswith("/debug/") and settings.app_environment in {"prod", "production"}:
            return await self._send_direct(send, 404, "Not Found", request_id, settings)
        if path in DOC_PATHS and not settings.enable_api_docs:
            return await self._send_direct(send, 404, "Not Found", request_id, settings)

        origin = headers.get("origin")
        if origin and origin not in settings.cors_allowed_origins and "*" not in settings.cors_allowed_origins:
            return await self._send_direct(send, 403, "Origin not allowed.", request_id, settings)
        if method == "OPTIONS" and origin:
            extra = [(b"access-control-allow-origin", origin.encode()), (b"access-control-allow-methods", b"POST, GET, OPTIONS"), (b"access-control-allow-headers", b"Authorization, Content-Type, X-Request-ID"), (b"vary", b"Origin")]
            return await self._send_direct(send, 200, "OK", request_id, settings, extra)

        if method == "POST" and path in SUPPORT_PATHS:
            media_type = headers.get("content-type", "").split(";", 1)[0].strip().casefold()
            if media_type != "application/json":
                return await self._send_direct(send, 415, "Content-Type must be application/json.", request_id, settings)
            content_length = headers.get("content-length")
            if content_length:
                try:
                    declared_length = int(content_length)
                except ValueError:
                    declared_length = -1
                if declared_length > settings.max_request_body_bytes:
                    return await self._send_direct(send, 413, "Request body too large.", request_id, settings)
            source = (scope.get("client") or ("unknown",))[0]
            decision = await self._limit("source:" + path + ":" + source, max(10, settings.rate_limit_requests * 10), settings.rate_limit_window_seconds)
            if decision is None:
                return await self._send_direct(send, 503, "Service temporarily unavailable.", request_id, settings)
            allowed, retry = decision
            if not allowed:
                return await self._send_direct(send, 429, "Too many requests.", request_id, settings, [(b"retry-after", str(retry).encode())])
            auth = headers.get("authorization", "")
            if auth:
                fingerprint = hashlib.sha256(auth.encode()).hexdigest()
                decision = await self._limit("credential:" + path + ":" + fingerprint, settings.rate_limit_requests, settings.rate_limit_window_seconds)
                if decision is None:
                    return await self._send_direct(send, 503, "Service temporarily unavailable.", request_id, settings)
                allowed, retry = decision
                if not allowed:
                    return await self._send_direct(send, 429, "Too many requests.", request_id, settings, [(b"retry-after", str(retry).encode())])
            body = bytearray()
            too_large = False
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > settings.max_request_body_bytes:
                    too_large = True
                if not message.get("more_body", False):
                    break
            if too_large:
                return await self._send_direct(send, 413, "Request body too large.", request_id, settings)
            delivered = False
            async def replay():
                nonlocal delivered
                if delivered:
                    return {"type": "http.disconnect"}
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            receive = replay

        status_code = 500
        async def secure_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                mutable = MutableHeaders(scope=message)
                self._headers(mutable, path, request_id, settings)
                if origin:
                    mutable["Access-Control-Allow-Origin"] = origin
                    mutable.add_vary_header("Origin")
            await send(message)
        try:
            await self.app(scope, receive, secure_send)
        finally:
            # Alembic's fileConfig may disable existing application loggers when
            # migrations run in-process; request logging must remain operational.
            logger.disabled = False
            logger.info(json.dumps({"request_id": request_id, "method": method, "path": path, "status": status_code, "duration_ms": round((time.monotonic() - started) * 1000, 2)}, separators=(",", ":")))

    async def _send_direct(self, send, status, detail, request_id, settings, extra=None):
        start, body = _response(status, detail, extra)
        mutable = MutableHeaders(scope=start)
        self._headers(mutable, "", request_id, settings)
        await send(start)
        await send(body)

    @staticmethod
    def _headers(headers, path, request_id, settings):
        headers["X-Request-ID"] = request_id
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "no-referrer"
        headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if path in SUPPORT_PATHS:
            headers["Cache-Control"] = "no-store"
        if settings.app_environment in {"prod", "production"} and settings.enable_hsts:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
