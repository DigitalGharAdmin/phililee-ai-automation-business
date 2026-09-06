import secrets
import unittest
import uuid
from dataclasses import replace
from unittest.mock import patch

from tests import TEST_SERVICE_KEY

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from firebase_admin import auth
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import require_n8n_service
from app.customer_auth import require_firebase_customer
from app.database import Base
from app.db_models import Customer
from app.firebase_auth import (
    FirebaseConfigurationError,
    FirebaseProviderUnavailableError,
    FirebaseTokenVerificationError,
    FirebaseTokenVerifier,
    VerifiedFirebaseIdentity,
)
from app.principals import (
    AuthenticationMethod,
    CustomerStatus,
    Permission,
    PrincipalType,
)
from app.settings import SETTINGS


class StubVerifier:
    def __init__(self, identity=None, error=None):
        self.identity = identity
        self.error = error
        self.tokens = []

    def verify(self, token):
        self.tokens.append(token)
        if self.error is not None:
            raise self.error
        return self.identity


class TestFirebaseTokenVerifier(unittest.TestCase):
    def verifier(self, *, check_revoked=False):
        return FirebaseTokenVerifier(
            settings=replace(
                SETTINGS,
                firebase_project_id="test-firebase-project",
                firebase_check_revoked=check_revoked,
            )
        )

    @patch("app.firebase_auth.firebase_admin.initialize_app")
    @patch("app.firebase_auth.firebase_admin.get_app")
    @patch("app.firebase_auth.auth.verify_id_token")
    def test_verified_identity_is_accepted_and_initialized_once(
        self, verify_id_token, get_app, initialize_app
    ):
        get_app.side_effect = ValueError("not initialized")
        firebase_app = object()
        initialize_app.return_value = firebase_app
        verify_id_token.return_value = {
            "uid": "verified-uid",
            "sub": "verified-uid",
            "admin": True,
            "scope": "untrusted-token-scope",
        }
        verifier = self.verifier(check_revoked=True)

        first = verifier.verify("firebase-id-token-one")
        second = verifier.verify("firebase-id-token-two")

        self.assertEqual(first, VerifiedFirebaseIdentity(uid="verified-uid"))
        self.assertEqual(second.uid, "verified-uid")
        self.assertFalse(hasattr(first, "scope"))
        initialize_app.assert_called_once_with(
            options={"projectId": "test-firebase-project"},
            name="customer-support-agent",
        )
        self.assertEqual(verify_id_token.call_count, 2)
        self.assertTrue(verify_id_token.call_args.kwargs["check_revoked"])
        self.assertIs(verify_id_token.call_args.kwargs["app"], firebase_app)

    @patch("app.firebase_auth.auth.verify_id_token")
    def test_provider_verification_failures_are_rejected(self, verify_id_token):
        failures = (
            ("invalid-signature", auth.InvalidIdTokenError("invalid signature")),
            ("expired", auth.ExpiredIdTokenError("expired", None)),
            ("wrong-audience", auth.InvalidIdTokenError("wrong audience")),
            ("wrong-issuer", auth.InvalidIdTokenError("wrong issuer")),
            ("revoked", auth.RevokedIdTokenError("revoked")),
        )
        verifier = self.verifier()
        verifier._app = object()
        for label, provider_error in failures:
            with self.subTest(label=label):
                verify_id_token.side_effect = provider_error
                with self.assertRaises(FirebaseTokenVerificationError):
                    verifier.verify(f"test-token-{label}")

    @patch("app.firebase_auth.auth.verify_id_token")
    def test_missing_or_inconsistent_verified_subject_is_rejected(
        self, verify_id_token
    ):
        verifier = self.verifier()
        verifier._app = object()
        for claims in ({}, {"uid": ""}, {"uid": "one", "sub": "two"}):
            with self.subTest(claims=claims):
                verify_id_token.return_value = claims
                with self.assertRaises(FirebaseTokenVerificationError):
                    verifier.verify("test-token")

    @patch("app.firebase_auth.auth.verify_id_token")
    def test_malformed_token_is_rejected_before_provider_call(self, verify_id_token):
        with self.assertRaises(FirebaseTokenVerificationError):
            self.verifier().verify("  ")
        verify_id_token.assert_not_called()

    def test_missing_project_configuration_fails_only_when_invoked(self):
        verifier = FirebaseTokenVerifier(
            settings=replace(SETTINGS, firebase_project_id=None)
        )
        with self.assertRaisesRegex(FirebaseConfigurationError, "FIREBASE_PROJECT_ID"):
            verifier.verify("test-token")


class TestFirebaseCustomerDependency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, class_=Session)
        Base.metadata.create_all(cls.engine)
        cls.customer_ids = {}
        with cls.SessionLocal() as db:
            for status in ("active", "disabled", "pending"):
                customer = Customer(
                    id=uuid.uuid4(),
                    auth_provider="firebase",
                    auth_subject=f"firebase-{status}",
                    display_name="Shared Display Name",
                    email="shared@example.invalid" if status == "active" else None,
                    status=status,
                )
                db.add(customer)
                cls.customer_ids[status] = customer.id
            db.commit()

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def credentials(self, token="test-firebase-id-token"):
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    def test_active_customer_maps_to_minimal_customer_principal(self):
        verifier = StubVerifier(VerifiedFirebaseIdentity(uid="firebase-active"))
        with self.SessionLocal() as db:
            principal = require_firebase_customer(self.credentials(), db, verifier)

        self.assertIs(principal.principal_type, PrincipalType.CUSTOMER)
        self.assertIs(
            principal.authentication_method,
            AuthenticationMethod.FIREBASE_ID_TOKEN,
        )
        self.assertEqual(principal.provider, "firebase")
        self.assertEqual(principal.subject, "firebase-active")
        self.assertEqual(principal.customer_id, self.customer_ids["active"])
        self.assertIs(principal.customer_status, CustomerStatus.ACTIVE)
        self.assertEqual(
            principal.permissions, frozenset({Permission.CUSTOMER_ORDER_ACCESS})
        )
        self.assertNotIn("test-firebase-id-token", repr(principal))

    def test_unknown_uid_and_non_identity_fields_cannot_substitute(self):
        for uid in ("unknown-uid", "Shared Display Name", "shared@example.invalid"):
            with self.subTest(uid=uid), self.SessionLocal() as db:
                verifier = StubVerifier(VerifiedFirebaseIdentity(uid=uid))
                with self.assertRaises(HTTPException) as raised:
                    require_firebase_customer(self.credentials(), db, verifier)
                self.assertEqual(raised.exception.status_code, 403)
                self.assertNotIn(uid, str(raised.exception.detail))

    def test_disabled_and_pending_customers_are_forbidden(self):
        for customer_status in ("disabled", "pending"):
            with self.subTest(status=customer_status), self.SessionLocal() as db:
                verifier = StubVerifier(
                    VerifiedFirebaseIdentity(uid=f"firebase-{customer_status}")
                )
                with self.assertRaises(HTTPException) as raised:
                    require_firebase_customer(self.credentials(), db, verifier)
                self.assertEqual(raised.exception.status_code, 403)

    def test_missing_malformed_and_invalid_tokens_are_unauthorized(self):
        scenarios = (
            (None, StubVerifier()),
            (
                HTTPAuthorizationCredentials(scheme="Basic", credentials="value"),
                StubVerifier(),
            ),
            (
                self.credentials("invalid-token"),
                StubVerifier(error=FirebaseTokenVerificationError("invalid")),
            ),
        )
        for credentials, verifier in scenarios:
            with self.subTest(credentials=credentials), self.SessionLocal() as db:
                with self.assertRaises(HTTPException) as raised:
                    require_firebase_customer(credentials, db, verifier)
                self.assertEqual(raised.exception.status_code, 401)

    def test_missing_firebase_configuration_is_unavailable(self):
        verifier = StubVerifier(error=FirebaseConfigurationError("not configured"))
        with self.SessionLocal() as db, self.assertRaises(HTTPException) as raised:
            require_firebase_customer(self.credentials(), db, verifier)
        self.assertEqual(raised.exception.status_code, 503)

    def test_provider_availability_failure_is_unavailable(self):
        verifier = StubVerifier(
            error=FirebaseProviderUnavailableError("provider unavailable")
        )
        with self.SessionLocal() as db, self.assertRaises(HTTPException) as raised:
            require_firebase_customer(self.credentials(), db, verifier)
        self.assertEqual(raised.exception.status_code, 503)

    def test_service_and_customer_credentials_never_fall_back(self):
        firebase_token = f"firebase-test-{secrets.token_urlsafe(32)}"
        with self.assertRaises(HTTPException) as service_rejection:
            require_n8n_service(self.credentials(firebase_token))
        self.assertEqual(service_rejection.exception.status_code, 401)

        rejecting_verifier = StubVerifier(
            error=FirebaseTokenVerificationError("invalid Firebase token")
        )
        with self.SessionLocal() as db, self.assertRaises(HTTPException) as customer_rejection:
            require_firebase_customer(
                self.credentials(TEST_SERVICE_KEY), db, rejecting_verifier
            )
        self.assertEqual(customer_rejection.exception.status_code, 401)
        self.assertEqual(rejecting_verifier.tokens, [TEST_SERVICE_KEY])


if __name__ == "__main__":
    unittest.main()
