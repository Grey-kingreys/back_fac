"""
apps/notifications/serializers.py
"""

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(
        source='get_type_notification_display', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'type_notification', 'type_label',
                  'titre', 'message', 'lien',
                  'est_lue', 'created_at']
        read_only_fields = fields
