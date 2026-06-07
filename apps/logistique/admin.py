from django.contrib import admin

from .models import DocumentVehicule, LigneMission, Maintenance, Mission, Panne, PositionGPS, Vehicule


@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
    list_display = ['immatriculation', 'type_vehicule', 'company',
                    'statut', 'chauffeur_attitré', 'has_nfc', 'is_active']
    list_filter = ['company', 'statut', 'type_vehicule', 'is_active']
    search_fields = ['immatriculation', 'marque', 'modele']


class LigneMissionInline(admin.TabularInline):
    model = LigneMission
    extra = 0


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'company', 'vehicule', 'chauffeur',
                    'depot_depart', 'depot_arrivee', 'statut', 'created_at']
    list_filter = ['company', 'statut']
    search_fields = ['numero', 'vehicule__immatriculation']
    readonly_fields = ['numero', 'qr_code', 'created_at', 'updated_at']
    inlines = [LigneMissionInline]


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = ['vehicule', 'type_maintenance', 'statut',
                    'date_planifiee', 'cout', 'created_at']
    list_filter = ['type_maintenance', 'statut']
    search_fields = ['vehicule__immatriculation']


@admin.register(Panne)
class PanneAdmin(admin.ModelAdmin):
    list_display = ['vehicule', 'statut', 'date_declaration',
                    'cout_reparation', 'declare_par']
    list_filter = ['statut']
    search_fields = ['vehicule__immatriculation']


@admin.register(DocumentVehicule)
class DocumentVehiculeAdmin(admin.ModelAdmin):
    list_display = ['vehicule', 'type_document', 'date_expiration', 'is_expire', 'created_at']
    list_filter = ['type_document']
    readonly_fields = ['created_at']
