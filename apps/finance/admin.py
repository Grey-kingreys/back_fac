from django.contrib import admin

from .models import (
    CaissePhysique,
    CompteMobileMoney,
    SessionCaisse,
    TauxChange,
    TransactionCaisse,
    TransactionMobileMoney,
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
