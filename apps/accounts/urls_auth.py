# apps/accounts/urls_auth.py
"""
URLs d'authentification.
À inclure dans config/urls.py : path("api/auth/", include("apps.accounts.urls_auth"))
"""

from django.urls import path

from .views_2fa import (
    TwoFactorDisableView,
    TwoFactorLoginVerifyView,
    TwoFactorResendView,
    TwoFactorSetupVerifyView,
    TwoFactorSetupView,
)
from .views_auth import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TokenRefreshView,
)
from .views_first_login import FirstLoginView


urlpatterns = [
    # ── Auth standard ─────────────────────────────────────────────────────
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('me/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),

    # ── Réinitialisation mot de passe (self-service) ───────────────────────
    path('password-reset/', PasswordResetRequestView.as_view(), name='auth-password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),

    # ── Première connexion Admin (créé par SuperAdmin) ─────────────────────
    path('first-login/', FirstLoginView.as_view(), name='auth-first-login'),

    # ── 2FA ────────────────────────────────────────────────────────────────
    # Configuration (utilisateur connecté)
    path('2fa/setup/', TwoFactorSetupView.as_view(), name='auth-2fa-setup'),
    path('2fa/setup-verify/', TwoFactorSetupVerifyView.as_view(), name='auth-2fa-setup-verify'),
    path('2fa/disable/', TwoFactorDisableView.as_view(), name='auth-2fa-disable'),
    # Vérification lors du login (AllowAny)
    path('2fa/login-verify/', TwoFactorLoginVerifyView.as_view(), name='auth-2fa-login-verify'),
    path('2fa/resend/', TwoFactorResendView.as_view(), name='auth-2fa-resend'),
]
