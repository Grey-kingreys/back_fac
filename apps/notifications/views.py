"""
apps/notifications/views.py
"""

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .models import Notification
from .serializers import NotificationSerializer


@extend_schema(tags=["Notifications"])
class NotificationViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = NotificationSerializer

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Notification.objects.filter(
            destinataire=self.request.user
        ).order_by('-created_at')
        non_lues_seulement = self.request.query_params.get('non_lues')
        if non_lues_seulement in ('true', '1'):
            qs = qs.filter(est_lue=False)
        return qs

    @extend_schema(summary="Marquer une notification comme lue")
    @action(detail=True, methods=['post'], url_path='lire')
    def lire(self, request, pk=None):
        notif = self.get_object()
        notif.est_lue = True
        notif.save(update_fields=['est_lue'])
        return Response(NotificationSerializer(notif).data)

    @extend_schema(summary="Marquer toutes les notifications comme lues")
    @action(detail=False, methods=['post'], url_path='tout-lire')
    def tout_lire(self, request):
        count = Notification.objects.filter(
            destinataire=request.user, est_lue=False
        ).update(est_lue=True)
        return Response({'detail': f"{count} notification(s) marquée(s) comme lue(s)."})
