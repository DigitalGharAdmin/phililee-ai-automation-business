from dataclasses import dataclass
from threading import Lock
from typing import Mapping

import firebase_admin
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError
from google.auth.exceptions import GoogleAuthError

from app.settings import SETTINGS, Settings


FIREBASE_PROVIDER = "firebase"
FIREBASE_APP_NAME = "customer-support-agent"


class FirebaseConfigurationError(RuntimeError):
    """Firebase customer authentication is not configured for this process."""


class FirebaseTokenVerificationError(ValueError):
    """A supplied credential is not a valid Firebase ID token."""


class FirebaseProviderUnavailableError(RuntimeError):
    """Firebase verification cannot currently be completed."""


@dataclass(frozen=True, slots=True)
class VerifiedFirebaseIdentity:
    uid: str


class FirebaseTokenVerifier:
    def __init__(
        self,
        *,
        settings: Settings = SETTINGS,
        check_revoked: bool | None = None,
    ) -> None:
        self._settings = settings
        self._check_revoked = (
            settings.firebase_check_revoked
            if check_revoked is None
            else check_revoked
        )
        self._app = None
        self._initialization_lock = Lock()

    def _get_app(self):
        project_id = self._settings.firebase_project_id
        if not project_id:
            raise FirebaseConfigurationError(
                "FIREBASE_PROJECT_ID is required for customer authentication."
            )

        if self._app is not None:
            return self._app

        with self._initialization_lock:
            if self._app is None:
                try:
                    self._app = firebase_admin.get_app(FIREBASE_APP_NAME)
                except ValueError:
                    self._app = firebase_admin.initialize_app(
                        options={"projectId": project_id},
                        name=FIREBASE_APP_NAME,
                    )
        return self._app

    def verify(self, id_token: str) -> VerifiedFirebaseIdentity:
        if not isinstance(id_token, str) or not id_token.strip():
            raise FirebaseTokenVerificationError(
                "Invalid Firebase customer credential."
            )

        try:
            claims: Mapping[str, object] = auth.verify_id_token(
                id_token,
                app=self._get_app(),
                check_revoked=self._check_revoked,
            )
        except FirebaseConfigurationError:
            raise
        except (
            ValueError,
            auth.InvalidIdTokenError,
            auth.ExpiredIdTokenError,
            auth.RevokedIdTokenError,
            auth.UserDisabledError,
        ) as exc:
            raise FirebaseTokenVerificationError(
                "Invalid Firebase customer credential."
            ) from exc
        except (auth.CertificateFetchError, FirebaseError, GoogleAuthError) as exc:
            raise FirebaseProviderUnavailableError(
                "Firebase customer verification is unavailable."
            ) from exc

        uid = claims.get("uid")
        subject = claims.get("sub")
        if not isinstance(uid, str) or not uid.strip():
            raise FirebaseTokenVerificationError(
                "Invalid Firebase customer credential."
            )
        if subject is not None and subject != uid:
            raise FirebaseTokenVerificationError(
                "Invalid Firebase customer credential."
            )
        return VerifiedFirebaseIdentity(uid=uid)


_DEFAULT_FIREBASE_VERIFIER: FirebaseTokenVerifier | None = None
_DEFAULT_VERIFIER_LOCK = Lock()


def get_firebase_token_verifier() -> FirebaseTokenVerifier:
    global _DEFAULT_FIREBASE_VERIFIER
    if _DEFAULT_FIREBASE_VERIFIER is None:
        with _DEFAULT_VERIFIER_LOCK:
            if _DEFAULT_FIREBASE_VERIFIER is None:
                _DEFAULT_FIREBASE_VERIFIER = FirebaseTokenVerifier()
    return _DEFAULT_FIREBASE_VERIFIER
