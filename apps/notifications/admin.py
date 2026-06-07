from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['destinataire', 'type_notification', 'titre', 'est_lue', 'created_at']
    list_filter = ['type_notification', 'est_lue']
    search_fields = ['destinataire__email', 'titre', 'message']
    readonly_fields = ['created_at']
