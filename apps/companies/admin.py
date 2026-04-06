from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Company, Depot, Zone


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


class DepotInline(admin.TabularInline):
    """Affiche les dépôts directement dans la fiche d'une Zone."""
    model = Depot
    extra = 0
    fields = ("code", "name", "address", "is_active")
    show_change_link = True


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "depot_count", "is_active", "created_at")
    list_filter = ("company", "is_active")
    search_fields = ("code", "name", "company__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DepotInline]
    fieldsets = (
        (None, {
            "fields": ("company", "name", "code", "description", "is_active"),
        }),
        (_("Dates"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description=_("Nb dépôts"))
    def depot_count(self, obj):
        return obj.depots.count()


@admin.register(Depot)
class DepotAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "zone", "company_name", "is_active", "created_at")
    list_filter = ("zone__company", "zone", "is_active")
    search_fields = ("code", "name", "zone__name", "zone__company__name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("zone", "name", "code", "address", "is_active"),
        }),
        (_("Dates"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description=_("Entreprise"))
    def company_name(self, obj):
        return obj.zone.company.name
