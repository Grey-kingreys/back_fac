# apps/accounts/audit_serializers.py
"""
R1-B09 — Serializers pour AuditLog et LoginLog
"""

from rest_framework import serializers

from .audit_models import AuditLog, LoginLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    action_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user',
            'user_email',
            'action',
            'action_display',
            'model_name',
            'object_id',
            'data_before',
            'data_after',
            'ip_address',
            'timestamp',
        ]
        read_only_fields = fields

    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        return None

    def get_action_display(self, obj):
        return obj.get_action_display()


class LoginLogSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = LoginLog
        fields = [
            'id',
            'user',
            'user_email',
            'ip_address',
            'user_agent',
            'success',
            'timestamp',
        ]
        read_only_fields = fields

    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        return None