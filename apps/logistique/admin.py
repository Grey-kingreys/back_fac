from django.contrib import admin

from .models import LigneMission, Mission, PositionGPS, Vehicule


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
    readonly_fields = ['numero', 'created_at', 'updated_at']
    inlines = [LigneMissionInline]
