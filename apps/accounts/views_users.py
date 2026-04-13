"""
apps/accounts/views_users.py
R1-B07 — CRUD Utilisateurs (API)

Endpoints :
  GET    /api/users/                  — liste paginée (Admin, Superviseur)
  POST   /api/users/                  — création (Admin uniquement)
  GET    /api/users/{id}/             — détail (Admin, Superviseur)
  PATCH  /api/users/{id}/             — modification partielle (Admin)
  DELETE /api/users/{id}/             — désactivation soft (Admin)
  POST   /api/users/{id}/reset-password/ — reset mot de passe (Admin)
"""

from django.contrib.auth import get_user_model

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole, IsCompanyMember
from apps.accounts.serializers import (
    AdminPasswordResetSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


@extend_schema(tags=["Utilisateurs"])
class UserViewSet(CompanyFilterMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin):
    """
    ViewSet de gestion des utilisateurs.
    - CompanyFilterMixin filtre automatiquement par company de l'user connecté.
    - Les permissions varient selon l'action (voir get_permissions).
    """

    queryset = User.objects.select_related('company', 'depot').order_by('last_name', 'first_name')

    # ── Permissions par action ──────────────────────────────────────────────
    def get_permissions(self):
        """
        - list / retrieve     : Admin ou Superviseur
        - create              : Admin uniquement
        - partial_update      : Admin uniquement
        - destroy             : Admin uniquement
        - reset_password      : Admin uniquement
        """
        admin_only = [
            HasRole([Role.ADMIN, Role.SUPERADMIN]),
            IsAuthenticated(),
        ]
        admin_or_supervisor = [
            HasRole([Role.ADMIN, Role.SUPERVISEUR, Role.SUPERADMIN]),
            IsAuthenticated(),
        ]

        if self.action in ('list', 'retrieve'):
            return admin_or_supervisor
        return admin_only

    # ── Serializer par action ───────────────────────────────────────────────
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'partial_update':
            return UserUpdateSerializer
        if self.action == 'reset_password':
            return AdminPasswordResetSerializer
        return UserDetailSerializer

    # ── Filtres query params ─────────────────────────────────────────────────
    def get_queryset(self):
        """
        Filtre de base par company (via CompanyFilterMixin),
        puis filtres additionnels via query params.
        """
        qs = super().get_queryset()

        role = self.request.query_params.get('role')
        depot = self.request.query_params.get('depot')
        is_active = self.request.query_params.get('is_active')

        if role:
            qs = qs.filter(role=role)
        if depot:
            qs = qs.filter(depot_id=depot)
        if is_active is not None:
            # Accepte "true"/"false" (Postman / Swagger) et "1"/"0"
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))

        return qs

    # ── GET /api/users/ ──────────────────────────────────────────────────────
    @extend_schema(
        summary="Lister les utilisateurs",
        description="Retourne la liste paginée des utilisateurs de la company. Filtres disponibles : ?role=, ?depot=, ?is_active=",
        parameters=[
            OpenApiParameter('role', description='Filtrer par rôle (ex: admin, caissier)', required=False),
            OpenApiParameter('depot', description='Filtrer par ID de dépôt', required=False),
            OpenApiParameter('is_active', description='Filtrer par statut actif (true/false)', required=False),
        ],
        responses={200: UserListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # ── GET /api/users/{id}/ ─────────────────────────────────────────────────
    @extend_schema(
        summary="Détail d'un utilisateur",
        responses={
            200: UserDetailSerializer,
            403: OpenApiResponse(description="Accès refusé — autre company"),
            404: OpenApiResponse(description="Utilisateur introuvable"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Vérification IsCompanyMember sur l'objet
        self._check_company(request, instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # ── POST /api/users/ ─────────────────────────────────────────────────────
    @extend_schema(
        summary="Créer un utilisateur",
        description="Admin uniquement. L'utilisateur est automatiquement rattaché à la company de l'admin.",
        request=UserCreateSerializer,
        responses={
            201: UserDetailSerializer,
            400: OpenApiResponse(description="Données invalides"),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserDetailSerializer(user, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    # ── PATCH /api/users/{id}/ ───────────────────────────────────────────────
    @extend_schema(
        summary="Modifier un utilisateur (partiel)",
        request=UserUpdateSerializer,
        responses={
            200: UserDetailSerializer,
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Accès refusé"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_company(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserDetailSerializer(user, context={'request': request}).data,
        )

    # ── DELETE /api/users/{id}/ ──────────────────────────────────────────────
    @extend_schema(
        summary="Désactiver un utilisateur (soft delete)",
        description="Ne supprime pas l'utilisateur — passe is_active à False.",
        responses={
            200: OpenApiResponse(description="Utilisateur désactivé"),
            400: OpenApiResponse(description="Impossible de se désactiver soi-même"),
            403: OpenApiResponse(description="Accès refusé"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_company(request, instance)

        # Empêcher l'admin de se désactiver lui-même
        if instance == request.user:
            return Response(
                {'detail': "Vous ne pouvez pas désactiver votre propre compte."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(
            {'detail': f"L'utilisateur {instance.get_full_name()} a été désactivé."},
            status=status.HTTP_200_OK,
        )

    # ── POST /api/users/{id}/reset-password/ ─────────────────────────────────
    @extend_schema(
        summary="Réinitialiser le mot de passe (par un admin)",
        request=AdminPasswordResetSerializer,
        responses={
            200: OpenApiResponse(description="Mot de passe réinitialisé"),
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Accès refusé"),
        },
    )
    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        instance = self.get_object()
        self._check_company(request, instance)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instance.set_password(serializer.validated_data['new_password'])
        instance.failed_attempts = 0
        instance.is_active = True  # Réactiver si le compte était bloqué
        instance.save(update_fields=['password', 'failed_attempts', 'is_active'])

        return Response(
            {'detail': f"Mot de passe de {instance.get_full_name()} réinitialisé avec succès."},
            status=status.HTTP_200_OK,
        )

    # ── Utilitaire ────────────────────────────────────────────────────────────
    def _check_company(self, request, instance):
        """
        Vérifie l'isolation company sur un objet.
        Lève 403 si l'utilisateur essaie d'accéder à une autre company.
        """
        perm = IsCompanyMember()
        if not perm.has_object_permission(request, self, instance):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'avez pas accès à cet utilisateur.")
