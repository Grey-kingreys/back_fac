# apps/accounts/audit_views.py
"""
R1-B09 — Vues API : GET /api/audit-logs/ et GET /api/login-logs/
Accès Admin uniquement (IsAdminOrSuperAdmin).
Filtres disponibles via query params.
"""

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .audit_models import AuditLog, LoginLog
from .audit_serializers import AuditLogSerializer, LoginLogSerializer
from .permissions import IsAdminOrSuperAdmin


class AuditLogListView(ListAPIView):
    """
    GET /api/audit-logs/
    Liste paginée des journaux d'audit.
    Accès : Admin et SuperAdmin uniquement.

    Filtres :
      ?model_name=CustomUser
      ?action=create|update|delete
      ?user_id=<id>
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    @extend_schema(
        summary="Journal d'audit",
        description=(
            "Liste paginée de toutes les actions create/update/delete "
            "effectuées sur les modèles sensibles (User, Zone, Depot).\n\n"
            "Filtres : `?model_name=CustomUser`, `?action=update`, `?user_id=3`"
        ),
        parameters=[
            OpenApiParameter('model_name', OpenApiTypes.STR, description="CustomUser | Zone | Depot"),
            OpenApiParameter('action', OpenApiTypes.STR, description="create | update | delete"),
            OpenApiParameter('user_id', OpenApiTypes.INT, description="ID de l'utilisateur ayant effectué l'action"),
        ],
        tags=["Audit"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user').order_by('-timestamp')

        # Isolation company : le SuperAdmin voit tout, l'Admin voit
        # uniquement les logs de sa company (via les user_id de sa company)
        user = self.request.user
        if not user.is_superadmin:
            company_user_ids = user.company.users.values_list('id', flat=True)
            qs = qs.filter(user_id__in=company_user_ids)

        # Filtres optionnels
        model_name = self.request.query_params.get('model_name')
        action = self.request.query_params.get('action')
        user_id = self.request.query_params.get('user_id')

        if model_name:
            qs = qs.filter(model_name=model_name)
        if action:
            qs = qs.filter(action=action)
        if user_id:
            qs = qs.filter(user_id=user_id)

        return qs


class LoginLogListView(ListAPIView):
    """
    GET /api/login-logs/
    Liste paginée des tentatives de connexion.
    Accès : Admin et SuperAdmin uniquement.

    Filtres :
      ?user_id=<id>
      ?success=true|false
    """
    serializer_class = LoginLogSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    @extend_schema(
        summary="Journal de connexion",
        description=(
            "Liste paginée de toutes les tentatives de connexion "
            "(succès et échecs) avec IP et user-agent.\n\n"
            "Filtres : `?user_id=3`, `?success=false`"
        ),
        parameters=[
            OpenApiParameter('user_id', OpenApiTypes.INT, description="Filtrer par utilisateur"),
            OpenApiParameter('success', OpenApiTypes.BOOL, description="true (réussies) | false (échouées)"),
        ],
        tags=["Audit"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = LoginLog.objects.select_related('user').order_by('-timestamp')

        user = self.request.user
        if not user.is_superadmin:
            company_user_ids = user.company.users.values_list('id', flat=True)
            # Inclut aussi les tentatives avec user=None (email inconnu)
            qs = qs.filter(user_id__in=company_user_ids)

        user_id = self.request.query_params.get('user_id')
        success = self.request.query_params.get('success')

        if user_id:
            qs = qs.filter(user_id=user_id)
        if success is not None:
            qs = qs.filter(success=success.lower() == 'true')

        return qs