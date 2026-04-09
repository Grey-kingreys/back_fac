"""
R1-B05 — URLs d'authentification
À inclure dans config/urls.py : path("api/auth/", include("apps.accounts.urls_auth"))
"""

from django.urls import path

from .views_auth import (
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TokenRefreshView,
)

urlpatterns = [
    # Authentification JWT
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),

    # Réinitialisation de mot de passe
    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
]
