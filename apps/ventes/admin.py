from django.contrib import admin

from .models import Client, Commande, LigneCommande, Paiement, ParametresFidelite


@admin.register(ParametresFidelite)
class ParametresFideliteAdmin(admin.ModelAdmin):
    list_display = ['company', 'is_active', 'tranche_montant',
                    'points_par_tranche', 'valeur_point_gnf']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom_complet', 'company', 'telephone',
                    'points_fidelite', 'solde_credit', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['code', 'nom', 'prenom', 'telephone']


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 0
    readonly_fields = ['montant_ht', 'montant_tva', 'montant_ttc']


class PaiementInline(admin.TabularInline):
    model = Paiement
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['numero', 'company', 'depot', 'client', 'statut',
                    'montant_ttc', 'montant_paye', 'mode_paiement', 'created_at']
    list_filter = ['company', 'depot', 'statut', 'mode_paiement']
    search_fields = ['numero', 'client__nom']
    readonly_fields = ['numero', 'created_at', 'updated_at']
    inlines = [LigneCommandeInline, PaiementInline]
