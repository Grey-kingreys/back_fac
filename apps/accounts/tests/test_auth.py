"""
R1-B05 — Tests d'authentification JWT
Lancer avec : pytest apps/accounts/tests/test_auth.py -v
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse

import pytest
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def active_user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="SecurePass123!",
        first_name="Test",
        last_name="User",
        role="ADMIN",
        is_active=True,
        failed_attempts=0,
    )


@pytest.fixture
def inactive_user(db):
    return User.objects.create_user(
        email="inactive@example.com",
        password="SecurePass123!",
        is_active=False,
    )


@pytest.fixture
def locked_user(db):
    user = User.objects.create_user(
        email="locked@example.com",
        password="SecurePass123!",
        is_active=True,
        failed_attempts=5,
    )
    return user


# ──────────────────────────────────────────────────────────────────────────────
# Tests — Login
# ──────────────────────────────────────────────────────────────────────────────

class TestLoginView:
    url = "/api/auth/login/"

    def test_login_success(self, api_client, active_user):
        res = api_client.post(self.url, {"email": "test@example.com", "password": "SecurePass123!"})
        assert res.status_code == status.HTTP_200_OK
        assert "access" in res.data
        assert "refresh" in res.data
        assert res.data["user"]["role"] == "ADMIN"

    def test_login_wrong_password(self, api_client, active_user):
        res = api_client.post(self.url, {"email": "test@example.com", "password": "wrongpassword"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_increments_failed_attempts(self, api_client, active_user):
        api_client.post(self.url, {"email": "test@example.com", "password": "wrong"})
        active_user.refresh_from_db()
        assert active_user.failed_attempts == 1

    def test_login_resets_failed_attempts_on_success(self, api_client, db):
        user = User.objects.create_user(
            email="retry@example.com",
            password="SecurePass123!",
            is_active=True,
            failed_attempts=3,
        )
        res = api_client.post(self.url, {"email": "retry@example.com", "password": "SecurePass123!"})
        assert res.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.failed_attempts == 0

    def test_login_inactive_user(self, api_client, inactive_user):
        res = api_client.post(self.url, {"email": "inactive@example.com", "password": "SecurePass123!"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_login_locked_account(self, api_client, locked_user):
        res = api_client.post(self.url, {"email": "locked@example.com", "password": "SecurePass123!"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_login_unknown_email(self, api_client, db):
        res = api_client.post(self.url, {"email": "nobody@example.com", "password": "any"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ──────────────────────────────────────────────────────────────────────────────
# Tests — Me
# ──────────────────────────────────────────────────────────────────────────────

class TestMeView:
    url = "/api/auth/me/"

    def test_me_authenticated(self, api_client, active_user):
        login = api_client.post("/api/auth/login/", {"email": "test@example.com", "password": "SecurePass123!"})
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        res = api_client.get(self.url)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["email"] == "test@example.com"

    def test_me_unauthenticated(self, api_client):
        res = api_client.get(self.url)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ──────────────────────────────────────────────────────────────────────────────
# Tests — Logout + Blacklist
# ──────────────────────────────────────────────────────────────────────────────

class TestLogoutView:
    def test_logout_blacklists_token(self, api_client, active_user):
        login = api_client.post("/api/auth/login/", {"email": "test@example.com", "password": "SecurePass123!"})
        access = login.data["access"]
        refresh = login.data["refresh"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        res = api_client.post("/api/auth/logout/", {"refresh": refresh})
        assert res.status_code == status.HTTP_200_OK

        # Le refresh token blacklisté ne peut plus générer d'access token
        res2 = api_client.post("/api/auth/refresh/", {"refresh": refresh})
        assert res2.status_code == status.HTTP_401_UNAUTHORIZED


# ──────────────────────────────────────────────────────────────────────────────
# Tests — Password Reset
# ──────────────────────────────────────────────────────────────────────────────

class TestPasswordReset:
    reset_url = "/api/auth/password-reset/"
    confirm_url = "/api/auth/password-reset/confirm/"

    def test_reset_request_unknown_email_same_response(self, api_client, db):
        """Anti-énumération : réponse identique email connu ou inconnu."""
        res = api_client.post(self.reset_url, {"email": "nobody@example.com"})
        assert res.status_code == status.HTTP_200_OK

    def test_reset_confirm_invalid_token(self, api_client, db):
        import uuid
        res = api_client.post(self.confirm_url, {
            "token": str(uuid.uuid4()),
            "new_password": "NewSecure123!",
            "new_password_confirm": "NewSecure123!",
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_confirm_password_mismatch(self, api_client, active_user):
        import uuid

        from django.core.cache import cache
        token = str(uuid.uuid4())
        cache.set(f"pwd_reset:{token}", {"user_id": active_user.id, "used": False}, timeout=3600)
        res = api_client.post(self.confirm_url, {
            "token": token,
            "new_password": "NewSecure123!",
            "new_password_confirm": "DifferentPass456!",
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_confirm_token_single_use(self, api_client, active_user):
        import uuid
        token = str(uuid.uuid4())
        cache.set(f"pwd_reset:{token}", {"user_id": active_user.id, "used": False}, timeout=3600)

        data = {"token": token, "new_password": "NewSecure123!", "new_password_confirm": "NewSecure123!"}
        res1 = api_client.post(self.confirm_url, data)
        assert res1.status_code == status.HTTP_200_OK

        # Deuxième utilisation — doit échouer
        res2 = api_client.post(self.confirm_url, data)
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
