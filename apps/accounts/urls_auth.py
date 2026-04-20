# apps/accounts/urls_auth.py
"""
URLs d'authentification.
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
from .views_first_login import FirstLoginView

urlpatterns = [
    # ── Auth standard ─────────────────────────────────────────────────────
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),

    # ── Réinitialisation mot de passe (self-service) ───────────────────────
    path('password-reset/', PasswordResetRequestView.as_view(), name='auth-password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),

    # ── Première connexion Admin (créé par SuperAdmin) ─────────────────────
    # GET  /api/auth/first-login/?token=<uuid>  — vérifier le token
    # POST /api/auth/first-login/               — définir le mot de passe
    path('first-login/', FirstLoginView.as_view(), name='auth-first-login'),
]
