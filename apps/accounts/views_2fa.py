"""
2FA — Vues pour la configuration et la vérification à deux facteurs.
Méthodes supportées : TOTP (app Authy/Authenticator) ou code par email.
"""

from django.contrib.auth import get_user_model

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .services_2fa import (
    create_temp_token,
    delete_setup_secret,
    generate_email_otp,
    generate_totp_secret,
    get_setup_secret,
    get_totp_qr_base64,
    invalidate_temp_token,
    resolve_temp_token,
    send_2fa_email,
    store_email_otp,
    store_setup_secret,
    verify_email_otp,
    verify_totp,
)


User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/2fa/setup/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth — 2FA"],
    summary="Initier la configuration 2FA",
    description=(
        "Démarre la configuration 2FA pour l'utilisateur connecté. "
        "Méthode 'totp' : retourne un QR code à scanner avec Authy. "
        "Méthode 'email' : envoie un code à 6 chiffres à l'adresse email."
    ),
    responses={
        200: OpenApiResponse(description="QR code ou confirmation d'envoi d'email"),
        400: OpenApiResponse(description="Méthode invalide"),
    },
)
class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        method = request.data.get('method', '')
        if method not in ('totp', 'email'):
            return Response(
                {'detail': "Méthode invalide. Choisissez 'totp' ou 'email'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        if method == 'totp':
            secret = generate_totp_secret()
            qr_code = get_totp_qr_base64(user, secret)
            store_setup_secret(user.id, secret)
            return Response({
                'method': 'totp',
                'secret': secret,
                'qr_code': qr_code,
                'message': 'Scannez le QR code avec Authy ou Google Authenticator, puis entrez le code affiché.',
            }, status=status.HTTP_200_OK)

        # email
        code = generate_email_otp()
        store_email_otp(user.id, code)
        send_2fa_email(user, code)
        return Response({
            'method': 'email',
            'message': f'Un code de vérification a été envoyé à {user.email}.',
        }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/2fa/setup-verify/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth — 2FA"],
    summary="Confirmer la configuration 2FA",
    description="Vérifie le code saisi pour activer définitivement la 2FA sur le compte.",
    responses={
        200: OpenApiResponse(description="2FA activée avec succès"),
        400: OpenApiResponse(description="Code invalide ou session expirée"),
    },
)
class TwoFactorSetupVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        method = request.data.get('method', '')
        code = str(request.data.get('code', '')).strip()
        user = request.user

        if not code or not code.isdigit() or len(code) != 6:
            return Response(
                {'detail': 'Le code doit être composé de 6 chiffres.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if method == 'totp':
            secret = get_setup_secret(user.id)
            if not secret:
                return Response(
                    {'detail': 'Session de configuration expirée. Recommencez.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not verify_totp(secret, code):
                return Response(
                    {'detail': 'Code invalide. Vérifiez votre application Authy.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            delete_setup_secret(user.id)
            user.totp_secret = secret
            user.two_factor_method = 'totp'
            user.two_factor_enabled = True
            user.save(update_fields=['totp_secret', 'two_factor_method', 'two_factor_enabled'])
            return Response(
                {'detail': '2FA activée avec succès. Utilisez votre app Authy à chaque connexion.'},
                status=status.HTTP_200_OK,
            )

        if method == 'email':
            if not verify_email_otp(user.id, code):
                return Response(
                    {'detail': 'Code invalide ou expiré.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.two_factor_method = 'email'
            user.two_factor_enabled = True
            user.save(update_fields=['two_factor_method', 'two_factor_enabled'])
            return Response(
                {'detail': '2FA activée avec succès. Un code vous sera envoyé par email à chaque connexion.'},
                status=status.HTTP_200_OK,
            )

        return Response(
            {'detail': "Méthode invalide. Choisissez 'totp' ou 'email'."},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/2fa/disable/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth — 2FA"],
    summary="Désactiver la 2FA",
    description="Désactive la 2FA sur le compte. Le mot de passe actuel est requis pour confirmation.",
    responses={
        200: OpenApiResponse(description="2FA désactivée"),
        400: OpenApiResponse(description="Mot de passe incorrect"),
    },
)
class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = request.data.get('password', '')
        if not password or not request.user.check_password(password):
            return Response(
                {'detail': 'Mot de passe incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        user.two_factor_enabled = False
        user.two_factor_method = ''
        user.totp_secret = ''
        user.save(update_fields=['two_factor_enabled', 'two_factor_method', 'totp_secret'])
        return Response(
            {'detail': '2FA désactivée avec succès.'},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/2fa/login-verify/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth — 2FA"],
    summary="Vérifier le code 2FA lors de la connexion",
    description=(
        "Deuxième étape du login. Reçoit le temp_token (retourné par /auth/login/ "
        "quand requires_2fa=true) et le code 2FA. Retourne les tokens JWT si valide."
    ),
    responses={
        200: OpenApiResponse(description="Tokens JWT (access + refresh + user)"),
        400: OpenApiResponse(description="Code invalide"),
        401: OpenApiResponse(description="Session expirée"),
    },
)
class TwoFactorLoginVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        temp_token = request.data.get('temp_token', '')
        code = str(request.data.get('code', '')).strip()

        if not temp_token:
            return Response(
                {'detail': "Le champ 'temp_token' est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not code or not code.isdigit() or len(code) != 6:
            return Response(
                {'detail': 'Le code doit être composé de 6 chiffres.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = resolve_temp_token(temp_token)
        if not payload:
            return Response(
                {'detail': 'Session expirée. Veuillez vous reconnecter.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user = User.objects.get(id=payload['user_id'], is_active=True)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Utilisateur introuvable.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        method = payload.get('method', 'totp')

        if method == 'totp':
            if not verify_totp(user.totp_secret, code):
                return Response(
                    {'detail': 'Code invalide. Vérifiez votre application Authy.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif method == 'email':
            if not verify_email_otp(user.id, code):
                return Response(
                    {'detail': 'Code invalide ou expiré.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {'detail': 'Méthode de vérification inconnue.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Code valide — invalider le token temporaire et émettre les JWT
        invalidate_temp_token(temp_token)

        if user.failed_attempts > 0:
            user.failed_attempts = 0
            user.save(update_fields=['failed_attempts'])

        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['company_id'] = user.company_id
        refresh['depot_id'] = user.depot_id

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'company_id': user.company_id,
                'depot_id': user.depot_id,
                'avatar': user.avatar.url if user.avatar else None,
                'two_factor_enabled': user.two_factor_enabled,
                'two_factor_method': user.two_factor_method,
            },
        }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/2fa/resend/
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth — 2FA"],
    summary="Renvoyer le code 2FA par email",
    description="Renvoie un nouveau code OTP par email. Uniquement disponible pour la méthode 'email'.",
    responses={
        200: OpenApiResponse(description="Nouveau code envoyé"),
        400: OpenApiResponse(description="Méthode incompatible"),
        401: OpenApiResponse(description="Session expirée"),
    },
)
class TwoFactorResendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        temp_token = request.data.get('temp_token', '')

        payload = resolve_temp_token(temp_token)
        if not payload:
            return Response(
                {'detail': 'Session expirée. Veuillez vous reconnecter.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if payload.get('method') != 'email':
            return Response(
                {'detail': "Le renvoi de code n'est disponible que pour la méthode email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=payload['user_id'], is_active=True)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Utilisateur introuvable.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        code = generate_email_otp()
        store_email_otp(user.id, code)
        send_2fa_email(user, code)

        return Response(
            {'detail': f'Nouveau code envoyé à {user.email}.'},
            status=status.HTTP_200_OK,
        )
