# apps/accounts/admin.py
"""
Interface d'administration — CustomUser, AuditLog, LoginLog.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser
from .audit_models import AuditLog, LoginLog


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'company', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'company')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('last_name', 'first_name')

    fieldsets = (
        (_('Connexion'), {
            'fields': ('email', 'password')
        }),
        (_('Informations personnelles'), {
            'fields': ('first_name', 'last_name', 'phone', 'avatar')
        }),
        (_('Organisation'), {
            'fields': ('company', 'depot', 'role')
        }),
        (_('Sécurité'), {
            'fields': ('failed_attempts',),
            'classes': ('collapse',),
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Métadonnées'), {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'failed_attempts')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'company', 'role', 'password1', 'password2'),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'object_id', 'ip_address']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__email', 'model_name', 'ip_address']
    readonly_fields = ['user', 'action', 'model_name', 'object_id',
                       'data_before', 'data_after', 'ip_address', 'timestamp']
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'success', 'ip_address', 'user_agent_short']
    list_filter = ['success', 'timestamp']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['user', 'ip_address', 'user_agent', 'success', 'timestamp']
    ordering = ['-timestamp']

    def user_agent_short(self, obj):
        return (obj.user_agent or '')[:60]
    user_agent_short.short_description = 'User-Agent'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False