"""
R1-B05 — Authentification JWT
Views : login, refresh, logout, me, password-reset, password-reset/confirm
"""

import uuid

from django.contrib.auth import get_user_model
from django.core.cache import cache

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers_auth import (
    LoginSerializer,
    MeSerializer,
    MessageSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    TokenRefreshSerializer,
    TokenResponseSerializer,
)
from .services import send_password_reset_email

User = get_user_model()

# ──────────────────────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────────────────────
MAX_FAILED_ATTEMPTS = 5
RESET_TOKEN_TTL = 3600  # 1 heure en secondes
RESET_CACHE_PREFIX = "pwd_reset:"


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/login/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Connexion utilisateur",
    description="Retourne un access token JWT et un refresh token. Le payload contient le rôle, la company et le dépôt de l'utilisateur.",
    request=LoginSerializer,
    responses={
        200: TokenResponseSerializer,
        401: OpenApiResponse(description="Identifiants invalides"),
        403: OpenApiResponse(description="Compte désactivé ou bloqué"),
    },
)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        # Récupération de l'utilisateur
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Identifiants invalides."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Vérification compte bloqué
        if not user.is_active:
            return Response(
                {"detail": "Ce compte est désactivé."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            return Response(
                {
                    "detail": (
                        f"Compte bloqué après {MAX_FAILED_ATTEMPTS} tentatives échouées. "
                        "Contactez votre administrateur."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérification du mot de passe
        if not user.check_password(password):
            user.failed_attempts += 1
            user.save(update_fields=["failed_attempts"])
            remaining = MAX_FAILED_ATTEMPTS - user.failed_attempts
            return Response(
                {
                    "detail": "Identifiants invalides.",
                    "attempts_remaining": max(remaining, 0),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Connexion réussie — reset failed_attempts
        if user.failed_attempts > 0:
            user.failed_attempts = 0
            user.save(update_fields=["failed_attempts"])

        # Génération des tokens JWT
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["company_id"] = user.company_id
        refresh["depot_id"] = user.depot_id

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "company_id": user.company_id,
                    "depot_id": user.depot_id,
                    "avatar": user.avatar.url if user.avatar else None,
                },
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/refresh/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Renouveler l'access token",
    description="Reçoit un refresh token valide et retourne un nouvel access token.",
    request=TokenRefreshSerializer,
    responses={
        200: OpenApiResponse(description="Nouvel access token"),
        401: OpenApiResponse(description="Refresh token invalide ou expiré"),
    },
)
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Le champ 'refresh' est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            return Response(
                {"access": str(refresh.access_token)},
                status=status.HTTP_200_OK,
            )
        except TokenError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Déconnexion",
    description="Blackliste le refresh token. L'access token expire naturellement selon JWT_ACCESS_MINUTES.",
    request=TokenRefreshSerializer,
    responses={
        200: OpenApiResponse(description="Déconnexion réussie"),
        400: OpenApiResponse(description="Refresh token manquant ou invalide"),
    },
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Le champ 'refresh' est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Déconnexion réussie."},
                status=status.HTTP_200_OK,
            )
        except TokenError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/auth/me/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Profil utilisateur connecté",
    description="Retourne le profil complet de l'utilisateur authentifié (rôle, company, dépôt, avatar).",
    responses={
        200: MeSerializer,
        401: OpenApiResponse(description="Non authentifié"),
    },
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/password-reset/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Demande de réinitialisation de mot de passe",
    description="Envoie un email avec un lien de réinitialisation valable 1h. La réponse est identique que l'email existe ou non (anti-énumération).",
    request=PasswordResetRequestSerializer,
    responses={200: MessageSerializer},
)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        # Réponse identique qu'il existe ou non — sécurité anti-énumération
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "Si cet email existe dans notre système, "
                        "vous recevrez un lien de réinitialisation."
                    )
                },
                status=status.HTTP_200_OK,
            )

        # Génération du token — UUID aléatoire stocké en cache
        reset_token = str(uuid.uuid4())
        cache_key = f"{RESET_CACHE_PREFIX}{reset_token}"
        cache.set(cache_key, {"user_id": user.id, "used": False}, timeout=RESET_TOKEN_TTL)

        # Envoi de l'email via Resend
        send_password_reset_email(user=user, token=reset_token)

        return Response(
            {
                "detail": (
                    "Si cet email existe dans notre système, "
                    "vous recevrez un lien de réinitialisation."
                )
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/password-reset/confirm/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Confirmer la réinitialisation du mot de passe",
    description="Reçoit le token reçu par email et le nouveau mot de passe. Le token est à usage unique et expire après 1h.",
    request=PasswordResetConfirmSerializer,
    responses={
        200: MessageSerializer,
        400: OpenApiResponse(description="Token invalide, expiré ou déjà utilisé"),
    },
)
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        cache_key = f"{RESET_CACHE_PREFIX}{token}"
        payload = cache.get(cache_key)

        if not payload:
            return Response(
                {"detail": "Lien de réinitialisation invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payload.get("used"):
            return Response(
                {"detail": "Ce lien a déjà été utilisé."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=payload["user_id"], is_active=True)
        except User.DoesNotExist:
            return Response(
                {"detail": "Utilisateur introuvable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mise à jour du mot de passe
        user.set_password(new_password)
        user.failed_attempts = 0  # reset aussi les tentatives échouées
        user.save(update_fields=["password", "failed_attempts"])

        # Invalider le token — usage unique
        payload["used"] = True
        cache.set(cache_key, payload, timeout=RESET_TOKEN_TTL)

        return Response(
            {"detail": "Mot de passe réinitialisé avec succès."},
            status=status.HTTP_200_OK,
        )
