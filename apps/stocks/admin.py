from django.contrib import admin

from .models import (
    AjustementStock,
    Inventaire,
    LigneInventaire,
    LigneTransfert,
    LotStock,
    MouvementStock,
    StockDepot,
    TransfertStock,
)


@admin.register(StockDepot)
class StockDepotAdmin(admin.ModelAdmin):
    list_display = ['produit', 'depot', 'quantite', 'updated_at']
    list_filter = ['depot__zone__company']
    search_fields = ['produit__nom', 'produit__reference', 'depot__code']


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ['produit', 'depot', 'type_mouvement', 'quantite',
                    'quantite_avant', 'quantite_apres', 'created_at']
    list_filter = ['type_mouvement', 'depot__zone__company']
    search_fields = ['produit__nom', 'reference_doc']
    readonly_fields = ['quantite_avant', 'quantite_apres', 'created_at']


class LigneTransfertInline(admin.TabularInline):
    model = LigneTransfert
    extra = 0


@admin.register(TransfertStock)
class TransfertStockAdmin(admin.ModelAdmin):
    list_display = ['numero', 'company', 'depot_source', 'depot_destination',
                    'statut', 'created_at']
    list_filter = ['statut', 'company']
    inlines = [LigneTransfertInline]


class LigneInventaireInline(admin.TabularInline):
    model = LigneInventaire
    extra = 0
    readonly_fields = ['quantite_theorique', 'ecart']


@admin.register(Inventaire)
class InventaireAdmin(admin.ModelAdmin):
    list_display = ['numero', 'company', 'depot', 'statut', 'cree_par', 'created_at']
    list_filter = ['statut', 'company']
    readonly_fields = ['numero', 'created_at', 'valide_le']
    inlines = [LigneInventaireInline]


@admin.register(AjustementStock)
class AjustementStockAdmin(admin.ModelAdmin):
    list_display = ['produit', 'depot', 'quantite', 'statut',
                    'demande_par', 'traite_par', 'created_at']
    list_filter = ['statut', 'depot__zone__company']
    readonly_fields = ['created_at', 'traite_le']
