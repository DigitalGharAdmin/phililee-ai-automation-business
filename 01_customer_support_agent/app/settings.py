import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOTENV_PATH = PROJECT_ROOT / ".env"
PRODUCTION_ENVIRONMENTS = {"prod", "production"}
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
KNOWN_ENVIRONMENTS = {"development", "test", "testing", "staging", "prod", "production"}
SERVICE_KEY_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    app_environment: str
    enable_debug_endpoints: bool
    database_url: str
    openai_api_key: str | None
    n8n_service_key_sha256: str
    firebase_project_id: str | None
    firebase_check_revoked: bool
    cors_allowed_origins: tuple[str, ...]
    trusted_hosts: tuple[str, ...]
    max_request_body_bytes: int
    rate_limit_requests: int
    rate_limit_window_seconds: int
    rate_limit_backend: str
    rate_limit_redis_url: str | None
    enable_api_docs: bool
    enable_hsts: bool
    db_pool_size: int
    db_max_overflow: int
    db_pool_timeout_seconds: int
    db_pool_recycle_seconds: int


def _value(
    name: str,
    environment: Mapping[str, str],
    dotenv: Mapping[str, str | None],
    default: str | None = None,
) -> str | None:
    # Deployment/process state is authoritative. The project .env is defaults only.
    if name in environment:
        return environment[name]
    value = dotenv.get(name)
    return value if value is not None else default


def _optional_bool(name: str, value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    normalized = value.strip().casefold()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ConfigurationError(f"{name} must be a boolean value.")


def _integer(name: str, value: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = default if value is None or not value.strip() else int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if not minimum <= parsed <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}.")
    return parsed


def _csv(name: str, value: str | None, default: str) -> tuple[str, ...]:
    items = tuple(item.strip() for item in (value or default).split(",") if item.strip())
    if not items:
        raise ConfigurationError(f"{name} must contain at least one value.")
    return items


def _origins(value: str | None) -> tuple[str, ...]:
    origins = _csv("CORS_ALLOWED_ORIGINS", value, "http://localhost:3000,http://localhost:5173")
    for origin in origins:
        parsed = urlsplit(origin)
        if origin == "*":
            continue
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or parsed.username:
            raise ConfigurationError("CORS_ALLOWED_ORIGINS contains an invalid origin.")
    return origins


def _hosts(value: str | None) -> tuple[str, ...]:
    hosts = _csv("TRUSTED_HOSTS", value, "testserver,localhost,127.0.0.1")
    if any(not re.fullmatch(r"\*|\*\.[A-Za-z0-9.-]+|[A-Za-z0-9.-]+", host) for host in hosts):
        raise ConfigurationError("TRUSTED_HOSTS contains an invalid host.")
    return hosts


def load_settings(
    *,
    environment: Mapping[str, str] | None = None,
    dotenv_path: Path | str | None = DEFAULT_DOTENV_PATH,
) -> Settings:
    """Build one validated settings snapshot without mutating ``os.environ``."""
    source_environment = os.environ if environment is None else environment
    dotenv = dotenv_values(dotenv_path) if dotenv_path is not None else {}

    app_environment = (
        _value("APP_ENV", source_environment, dotenv, "development") or "development"
    ).strip().casefold()
    if app_environment not in KNOWN_ENVIRONMENTS:
        raise ConfigurationError("APP_ENV is invalid.")
    debug_value = _value("ENABLE_DEBUG_ENDPOINTS", source_environment, dotenv)
    enable_debug_endpoints = (
        debug_value.strip().casefold() in TRUE_VALUES
        if debug_value is not None
        else app_environment not in PRODUCTION_ENVIRONMENTS
    )
    if app_environment in PRODUCTION_ENVIRONMENTS:
        enable_debug_endpoints = False

    service_digest = (
        _value("N8N_SERVICE_KEY_SHA256", source_environment, dotenv, "") or ""
    ).strip().casefold()
    if not service_digest:
        raise ConfigurationError(
            "N8N_SERVICE_KEY_SHA256 is required because /support service "
            "authentication is enabled."
        )
    if not SERVICE_KEY_DIGEST_PATTERN.fullmatch(service_digest):
        raise ConfigurationError(
            "N8N_SERVICE_KEY_SHA256 must be exactly 64 hexadecimal characters."
        )

    firebase_project_id_value = _value(
        "FIREBASE_PROJECT_ID", source_environment, dotenv
    )
    firebase_project_id = (
        firebase_project_id_value.strip() if firebase_project_id_value else None
    ) or None
    firebase_check_revoked = _optional_bool(
        "FIREBASE_CHECK_REVOKED",
        _value("FIREBASE_CHECK_REVOKED", source_environment, dotenv),
        False,
    )
    database_url = _value("DATABASE_URL", source_environment, dotenv, "sqlite+pysqlite:///./customer_support.db") or "sqlite+pysqlite:///./customer_support.db"
    cors_allowed_origins = _origins(_value("CORS_ALLOWED_ORIGINS", source_environment, dotenv))
    trusted_hosts = _hosts(_value("TRUSTED_HOSTS", source_environment, dotenv))
    rate_limit_backend = (_value("RATE_LIMIT_BACKEND", source_environment, dotenv, "memory") or "memory").strip().casefold()
    if rate_limit_backend not in {"memory", "external"}:
        raise ConfigurationError("RATE_LIMIT_BACKEND must be memory or external.")
    rate_limit_redis_url = _value("RATE_LIMIT_REDIS_URL", source_environment, dotenv)
    rate_limit_redis_url = rate_limit_redis_url.strip() if rate_limit_redis_url else None
    if rate_limit_redis_url and not rate_limit_redis_url.startswith(("redis://", "rediss://")):
        raise ConfigurationError("RATE_LIMIT_REDIS_URL must use redis:// or rediss://.")
    enable_api_docs = _optional_bool("ENABLE_API_DOCS", _value("ENABLE_API_DOCS", source_environment, dotenv), app_environment not in PRODUCTION_ENVIRONMENTS)
    enable_hsts = _optional_bool("ENABLE_HSTS", _value("ENABLE_HSTS", source_environment, dotenv), False)
    if app_environment in PRODUCTION_ENVIRONMENTS:
        if "*" in cors_allowed_origins:
            raise ConfigurationError("CORS_ALLOWED_ORIGINS cannot contain a wildcard in production.")
        if "*" in trusted_hosts:
            raise ConfigurationError("TRUSTED_HOSTS cannot contain a wildcard in production.")
        if rate_limit_backend != "external":
            raise ConfigurationError("RATE_LIMIT_BACKEND must be external in production.")
        if not rate_limit_redis_url:
            raise ConfigurationError("RATE_LIMIT_REDIS_URL is required in production.")
        if not firebase_project_id:
            raise ConfigurationError("FIREBASE_PROJECT_ID is required in production.")
        if not database_url.startswith(("postgresql://", "postgresql+")):
            raise ConfigurationError("DATABASE_URL must use PostgreSQL in production.")

    return Settings(
        app_environment=app_environment,
        enable_debug_endpoints=enable_debug_endpoints,
        database_url=database_url,
        openai_api_key=_value("OPENAI_API_KEY", source_environment, dotenv),
        n8n_service_key_sha256=service_digest,
        firebase_project_id=firebase_project_id,
        firebase_check_revoked=firebase_check_revoked,
        cors_allowed_origins=cors_allowed_origins,
        trusted_hosts=trusted_hosts,
        max_request_body_bytes=_integer("MAX_REQUEST_BODY_BYTES", _value("MAX_REQUEST_BODY_BYTES", source_environment, dotenv), 65536, 1024, 1048576),
        rate_limit_requests=_integer("RATE_LIMIT_REQUESTS", _value("RATE_LIMIT_REQUESTS", source_environment, dotenv), 1000, 1, 100000),
        rate_limit_window_seconds=_integer("RATE_LIMIT_WINDOW_SECONDS", _value("RATE_LIMIT_WINDOW_SECONDS", source_environment, dotenv), 60, 1, 3600),
        rate_limit_backend=rate_limit_backend,
        rate_limit_redis_url=rate_limit_redis_url,
        enable_api_docs=enable_api_docs,
        enable_hsts=enable_hsts,
        db_pool_size=_integer("DB_POOL_SIZE", _value("DB_POOL_SIZE", source_environment, dotenv), 5, 1, 100),
        db_max_overflow=_integer("DB_MAX_OVERFLOW", _value("DB_MAX_OVERFLOW", source_environment, dotenv), 10, 0, 100),
        db_pool_timeout_seconds=_integer("DB_POOL_TIMEOUT_SECONDS", _value("DB_POOL_TIMEOUT_SECONDS", source_environment, dotenv), 30, 1, 300),
        db_pool_recycle_seconds=_integer("DB_POOL_RECYCLE_SECONDS", _value("DB_POOL_RECYCLE_SECONDS", source_environment, dotenv), 1800, 30, 86400),
    )


SETTINGS = load_settings()


def debug_endpoints_enabled() -> bool:
    return SETTINGS.enable_debug_endpoints
