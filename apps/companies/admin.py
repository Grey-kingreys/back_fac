from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'subscription_plan', 'is_active', 'created_at')
    list_filter = ('is_active', 'subscription_plan')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Informations principales', {
            'fields': ('name', 'slug', 'logo', 'is_active')
        }),
        ('Abonnement', {
            'fields': ('subscription_plan',)
        }),
        ('Configuration', {
            'fields': ('settings',),
            'classes': ('collapse',),
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
        }),
    )
