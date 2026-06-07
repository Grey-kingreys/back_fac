from django.contrib import admin

from .models import (
    Client,
    Commande,
    Devis,
    HistoriquePoints,
    LigneCommande,
    Paiement,
    ParametresFidelite,
    RetourCommande,
)


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


@admin.register(HistoriquePoints)
class HistoriquePointsAdmin(admin.ModelAdmin):
    list_display = ['client', 'type_mouvement', 'points', 'commande', 'created_at']
    list_filter = ['type_mouvement']
    readonly_fields = ['created_at']


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display = ['numero', 'company', 'client', 'statut', 'date_expiration', 'created_at']
    list_filter = ['company', 'statut']
    search_fields = ['numero']
    readonly_fields = ['numero', 'created_at', 'updated_at']


@admin.register(RetourCommande)
class RetourCommandeAdmin(admin.ModelAdmin):
    list_display = ['commande', 'motif', 'type_retour', 'montant_rembourse', 'created_at']
    list_filter = ['motif', 'type_retour']
    readonly_fields = ['created_at']
