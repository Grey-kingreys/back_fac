# apps/accounts/views_first_login.py
"""
Endpoint de première connexion pour les Admins créés par le SuperAdmin.

GET  /api/auth/first-login/?token=<uuid>  — vérifier si le token est valide
POST /api/auth/first-login/               — définir le mot de passe + activer le compte
"""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class FirstLoginView(APIView):
    """
    GET  : vérifie que le token existe et n'a pas encore été utilisé.
           Le frontend appelle cet endpoint au chargement de la page
           pour afficher le formulaire ou une erreur.

    POST : valide le token, définit le mot de passe, active le compte
           et retourne un JWT pour connecter l'Admin directement.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Vérifier un token de première connexion",
        description=(
            "Vérifie que le token est valide et n'a pas encore été utilisé.\n\n"
            "Appelé par le frontend au chargement de `/auth/first-login?token=<uuid>`."
        ),
        parameters=[
            OpenApiParameter('token', description="UUID reçu par email", required=True),
        ],
        responses={
            200: OpenApiResponse(description="Token valide — retourne l'email et le nom de la company"),
            400: OpenApiResponse(description="Token manquant"),
            404: OpenApiResponse(description="Token invalide ou déjà utilisé"),
        },
        tags=["Auth"],
    )
    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            return Response(
                {'success': False, 'message': "Token manquant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            first_login_token=token,
            first_login_done=False,
        ).select_related('company').first()

        if not user:
            return Response(
                {'success': False, 'message': "Ce lien est invalide ou a déjà été utilisé."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'success': True,
            'data': {
                'email': user.email,
                'company': user.company.name if user.company else None,
            },
            'message': "Token valide."
        })

    @extend_schema(
        summary="Définir le mot de passe via le lien de première connexion",
        description=(
            "Valide le token, définit le mot de passe de l'Admin et active son compte.\n\n"
            "Retourne un JWT pour connecter l'Admin directement sans qu'il ait "
            "à se reconnecter.\n\n"
            "Le token est invalidé immédiatement après usage."
        ),
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'token': {'type': 'string', 'format': 'uuid'},
                    'password': {'type': 'string', 'minLength': 8},
                    'password_confirm': {'type': 'string'},
                },
                'required': ['token', 'password', 'password_confirm'],
            }
        },
        responses={
            200: OpenApiResponse(description="Compte activé — retourne access + refresh JWT"),
            400: OpenApiResponse(description="Token invalide, déjà utilisé ou mots de passe non concordants"),
        },
        tags=["Auth"],
    )
    def post(self, request):
        token = request.data.get('token')
        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')

        # Validations basiques
        if not token:
            return Response(
                {'success': False, 'message': "Token manquant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not password or not password_confirm:
            return Response(
                {'success': False, 'message': "Le mot de passe est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password != password_confirm:
            return Response(
                {'success': False, 'errors': {'password_confirm': "Les mots de passe ne correspondent pas."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(password) < 8:
            return Response(
                {'success': False, 'errors': {'password': "Le mot de passe doit contenir au moins 8 caractères."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Recherche de l'utilisateur via le token
        user = User.objects.filter(
            first_login_token=token,
            first_login_done=False,
        ).select_related('company').first()

        if not user:
            return Response(
                {'success': False, 'message': "Ce lien est invalide ou a déjà été utilisé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Définir le mot de passe, activer le compte, invalider le token
        user.set_password(password)
        user.is_active = True
        user.first_login_done = True
        user.first_login_token = None  # usage unique — token invalidé
        user.save(update_fields=['password', 'is_active', 'first_login_done', 'first_login_token'])

        # Générer un JWT pour connecter l'Admin directement
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['company_id'] = user.company_id

        return Response({
            'success': True,
            'data': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'company_id': user.company_id,
                    'company': user.company.name if user.company else None,
                },
            },
            'message': "Mot de passe défini avec succès. Bienvenue !"
        })