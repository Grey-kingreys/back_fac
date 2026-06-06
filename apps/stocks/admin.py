from django.contrib import admin

from .models import LigneTransfert, LotStock, MouvementStock, StockDepot, TransfertStock


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
