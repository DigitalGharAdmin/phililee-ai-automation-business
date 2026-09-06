import hashlib
import secrets
import tempfile
import unittest
from pathlib import Path

from app.settings import ConfigurationError, load_settings


class TestSettingsLoading(unittest.TestCase):
    def setUp(self):
        self.digest = hashlib.sha256(secrets.token_bytes(48)).hexdigest()

    def write_dotenv(self, directory: str, value: str) -> Path:
        path = Path(directory) / ".env"
        path.write_text(f"N8N_SERVICE_KEY_SHA256={value}\n", encoding="utf-8")
        return path

    def test_valid_digest_is_accepted_and_safely_normalized(self):
        settings = load_settings(
            environment={"N8N_SERVICE_KEY_SHA256": f"  {self.digest.upper()}  "},
            dotenv_path=None,
        )
        self.assertEqual(settings.n8n_service_key_sha256, self.digest)

    def test_missing_digest_fails_clearly(self):
        with self.assertRaisesRegex(ConfigurationError, "required"):
            load_settings(environment={}, dotenv_path=None)

    def test_invalid_length_digest_fails(self):
        with self.assertRaisesRegex(ConfigurationError, "64 hexadecimal"):
            load_settings(
                environment={"N8N_SERVICE_KEY_SHA256": self.digest[:-1]},
                dotenv_path=None,
            )

    def test_non_hex_digest_fails(self):
        with self.assertRaisesRegex(ConfigurationError, "64 hexadecimal"):
            load_settings(
                environment={"N8N_SERVICE_KEY_SHA256": "g" * 64},
                dotenv_path=None,
            )

    def test_process_environment_takes_precedence_over_dotenv(self):
        process_digest = hashlib.sha256(secrets.token_bytes(48)).hexdigest()
        dotenv_digest = hashlib.sha256(secrets.token_bytes(48)).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            dotenv_path = self.write_dotenv(directory, dotenv_digest)
            settings = load_settings(
                environment={"N8N_SERVICE_KEY_SHA256": process_digest},
                dotenv_path=dotenv_path,
            )
        self.assertEqual(settings.n8n_service_key_sha256, process_digest)

    def test_dotenv_supplies_missing_process_value(self):
        with tempfile.TemporaryDirectory() as directory:
            dotenv_path = self.write_dotenv(directory, self.digest)
            settings = load_settings(environment={}, dotenv_path=dotenv_path)
        self.assertEqual(settings.n8n_service_key_sha256, self.digest)

    def test_fresh_initializations_are_deterministic(self):
        environment = {"N8N_SERVICE_KEY_SHA256": self.digest}
        first = load_settings(environment=environment, dotenv_path=None)
        second = load_settings(environment=environment, dotenv_path=None)
        self.assertEqual(first, second)

    def test_firebase_project_environment_precedes_dotenv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                f"N8N_SERVICE_KEY_SHA256={self.digest}\n"
                "FIREBASE_PROJECT_ID=dotenv-project\n",
                encoding="utf-8",
            )
            settings = load_settings(
                environment={
                    "N8N_SERVICE_KEY_SHA256": self.digest,
                    "FIREBASE_PROJECT_ID": "process-project",
                },
                dotenv_path=path,
            )
        self.assertEqual(settings.firebase_project_id, "process-project")

    def test_firebase_configuration_is_optional_until_customer_auth_is_used(self):
        settings = load_settings(
            environment={"N8N_SERVICE_KEY_SHA256": self.digest},
            dotenv_path=None,
        )
        self.assertIsNone(settings.firebase_project_id)
        self.assertFalse(settings.firebase_check_revoked)

    def test_invalid_firebase_revocation_policy_fails_clearly(self):
        with self.assertRaisesRegex(ConfigurationError, "FIREBASE_CHECK_REVOKED"):
            load_settings(
                environment={
                    "N8N_SERVICE_KEY_SHA256": self.digest,
                    "FIREBASE_CHECK_REVOKED": "invalid",
                },
                dotenv_path=None,
            )

    def production_environment(self):
        return {
            "N8N_SERVICE_KEY_SHA256": self.digest,
            "APP_ENV": "production",
            "DATABASE_URL": "postgresql+psycopg://user:password@db.example/app",
            "FIREBASE_PROJECT_ID": "production-project",
            "CORS_ALLOWED_ORIGINS": "https://app.example",
            "TRUSTED_HOSTS": "api.example",
            "RATE_LIMIT_BACKEND": "external",
            "RATE_LIMIT_REDIS_URL": "rediss://redis.example/0",
        }

    def test_valid_production_security_configuration(self):
        settings = load_settings(environment=self.production_environment(), dotenv_path=None)
        self.assertFalse(settings.enable_api_docs)
        self.assertFalse(settings.enable_debug_endpoints)
        self.assertEqual(settings.rate_limit_backend, "external")

    def test_production_rejects_wildcards_and_memory_only_rate_limit(self):
        for name, value in (("CORS_ALLOWED_ORIGINS", "*"), ("TRUSTED_HOSTS", "*"), ("RATE_LIMIT_BACKEND", "memory")):
            with self.subTest(name=name):
                environment = self.production_environment()
                environment[name] = value
                with self.assertRaises(ConfigurationError):
                    load_settings(environment=environment, dotenv_path=None)

    def test_malformed_origins_hosts_and_integer_ranges_are_rejected(self):
        cases = (("CORS_ALLOWED_ORIGINS", "javascript:bad"), ("TRUSTED_HOSTS", "bad host"), ("MAX_REQUEST_BODY_BYTES", "12"), ("DB_POOL_SIZE", "zero"), ("RATE_LIMIT_REQUESTS", "0"))
        for name, value in cases:
            with self.subTest(name=name):
                environment = {"N8N_SERVICE_KEY_SHA256": self.digest, name: value}
                with self.assertRaises(ConfigurationError):
                    load_settings(environment=environment, dotenv_path=None)

    def test_external_limiter_requires_valid_redis_url_in_production(self):
        environment = self.production_environment()
        environment.pop("RATE_LIMIT_REDIS_URL")
        with self.assertRaisesRegex(ConfigurationError, "RATE_LIMIT_REDIS_URL"):
            load_settings(environment=environment, dotenv_path=None)
        environment["RATE_LIMIT_REDIS_URL"] = "https://not-redis.example"
        with self.assertRaisesRegex(ConfigurationError, "redis"):
            load_settings(environment=environment, dotenv_path=None)

    def test_unknown_environment_is_rejected_without_echoing_values(self):
        with self.assertRaises(ConfigurationError) as raised:
            load_settings(environment={"N8N_SERVICE_KEY_SHA256": self.digest, "APP_ENV": "unsafe-secret-value"}, dotenv_path=None)
        self.assertNotIn("unsafe-secret-value", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
