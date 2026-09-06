import secrets
import unittest
import uuid
from dataclasses import fields

from tests import TEST_SERVICE_KEY

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import require_n8n_service, require_n8n_support_service
from app.authorization import require_permissions
from app.principals import (
    AuthenticatedPrincipal,
    AuthenticationMethod,
    CustomerStatus,
    Permission,
    PrincipalType,
    create_n8n_service_principal,
)


class TestAuthenticatedPrincipals(unittest.TestCase):
    def customer_principal(self) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(
            principal_type=PrincipalType.CUSTOMER,
            subject="verified-provider-subject",
            authentication_method=AuthenticationMethod.OIDC,
            customer_id=uuid.uuid4(),
            provider="test-provider",
            customer_status=CustomerStatus.ACTIVE,
        )

    def test_service_principal_creation_is_minimal_and_typed(self):
        principal = create_n8n_service_principal()
        self.assertIs(principal.principal_type, PrincipalType.SERVICE)
        self.assertEqual(principal.subject, "n8n")
        self.assertEqual(
            principal.permissions, frozenset({Permission.SUPPORT_OPERATIONS})
        )
        self.assertIsNone(principal.customer_id)

    def test_customer_principal_representation(self):
        principal = self.customer_principal()
        self.assertIs(principal.principal_type, PrincipalType.CUSTOMER)
        self.assertIsInstance(principal.customer_id, uuid.UUID)
        self.assertIs(principal.customer_status, CustomerStatus.ACTIVE)

    def test_invalid_principal_states_are_rejected(self):
        invalid_values = (
            {
                "principal_type": "unknown",
                "subject": "subject",
                "authentication_method": AuthenticationMethod.OIDC,
            },
            {
                "principal_type": PrincipalType.CUSTOMER,
                "subject": "subject",
                "authentication_method": AuthenticationMethod.OIDC,
            },
            {
                "principal_type": PrincipalType.SERVICE,
                "subject": "service",
                "authentication_method": AuthenticationMethod.N8N_SERVICE_KEY,
                "customer_id": uuid.uuid4(),
            },
        )
        for values in invalid_values:
            with self.subTest(values=values), self.assertRaises(ValueError):
                AuthenticatedPrincipal(**values)

    def test_principal_has_no_raw_credential_storage(self):
        field_names = {field.name for field in fields(AuthenticatedPrincipal)}
        self.assertTrue(
            field_names.isdisjoint({"credential", "service_key", "token", "digest"})
        )
        self.assertNotIn(TEST_SERVICE_KEY, repr(create_n8n_service_principal()))

    def test_valid_service_key_produces_scoped_service_principal(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=TEST_SERVICE_KEY
        )
        principal = require_n8n_service(credentials)
        authorized = require_n8n_support_service(principal)
        self.assertIs(authorized.principal_type, PrincipalType.SERVICE)
        self.assertIn(Permission.SUPPORT_OPERATIONS, authorized.permissions)

    def test_missing_and_invalid_service_keys_remain_unauthorized(self):
        invalid_credentials = (
            None,
            HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=secrets.token_urlsafe(48)
            ),
            HTTPAuthorizationCredentials(scheme="Basic", credentials="not-bearer"),
        )
        for credentials in invalid_credentials:
            with self.subTest(credentials_present=credentials is not None):
                with self.assertRaises(HTTPException) as raised:
                    require_n8n_service(credentials)
                self.assertEqual(raised.exception.status_code, 401)
                self.assertNotIn(TEST_SERVICE_KEY, str(raised.exception.detail))

    def test_required_scope_succeeds(self):
        principal = create_n8n_service_principal()
        self.assertIs(
            require_permissions(principal, {Permission.SUPPORT_OPERATIONS}),
            principal,
        )

    def test_missing_or_unrelated_scope_is_forbidden(self):
        for permissions in (
            frozenset(),
            frozenset({Permission.CUSTOMER_ORDER_ACCESS}),
        ):
            principal = AuthenticatedPrincipal(
                principal_type=PrincipalType.SERVICE,
                subject="restricted-service",
                authentication_method=AuthenticationMethod.N8N_SERVICE_KEY,
                permissions=permissions,
            )
            with self.assertRaises(HTTPException) as raised:
                require_permissions(principal, {Permission.SUPPORT_OPERATIONS})
            self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
