from django.contrib import admin

from .models import (
    CaisseEntreprise,
    CaissePhysique,
    CaisseZone,
    CompteMobileMoney,
    SessionCaisse,
    TauxChange,
    TransactionCaisse,
    TransactionMobileMoney,
    VersementCaisse,
)


@admin.register(TauxChange)
class TauxChangeAdmin(admin.ModelAdmin):
    list_display = ['company', 'devise_source', 'devise_cible', 'taux',
                    'date_expiration', 'created_at']
    list_filter = ['company', 'devise_source', 'devise_cible']


@admin.register(CaissePhysique)
class CaissePhysiqueAdmin(admin.ModelAdmin):
    list_display = ['nom', 'company', 'depot', 'solde_actuel', 'is_active']
    list_filter = ['company', 'is_active']


class TransactionCaisseInline(admin.TabularInline):
    model = TransactionCaisse
    extra = 0
    readonly_fields = ['created_at']


@admin.register(SessionCaisse)
class SessionCaisseAdmin(admin.ModelAdmin):
    list_display = ['pk', 'caisse', 'caissier', 'statut',
                    'solde_ouverture', 'ecart', 'ouvert_le', 'ferme_le']
    list_filter = ['caisse__company', 'statut']
    readonly_fields = ['ouvert_le', 'ferme_le']
    inlines = [TransactionCaisseInline]


@admin.register(CompteMobileMoney)
class CompteMobileMoneyAdmin(admin.ModelAdmin):
    list_display = ['numero', 'operateur', 'company', 'depot',
                    'nom_titulaire', 'solde', 'is_active']
    list_filter = ['company', 'operateur', 'is_active']


@admin.register(TransactionMobileMoney)
class TransactionMobileMoneyAdmin(admin.ModelAdmin):
    list_display = ['compte', 'type_transaction', 'montant',
                    'reference_operateur', 'created_at']
    list_filter = ['compte__company', 'type_transaction']


@admin.register(CaisseZone)
class CaisseZoneAdmin(admin.ModelAdmin):
    list_display = ['nom', 'company', 'zone', 'devise', 'solde_actuel', 'is_active']
    list_filter = ['company', 'is_active']


@admin.register(CaisseEntreprise)
class CaisseEntrepriseAdmin(admin.ModelAdmin):
    list_display = ['nom', 'company', 'devise', 'solde_actuel', 'is_active']
    list_filter = ['is_active']


@admin.register(VersementCaisse)
class VersementCaisseAdmin(admin.ModelAdmin):
    list_display = ['type_versement', 'montant', 'effectue_par', 'created_at']
    list_filter = ['type_versement']
    readonly_fields = ['created_at']
