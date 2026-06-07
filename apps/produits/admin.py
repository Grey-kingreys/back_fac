from django.contrib import admin

from .models import (
    Categorie,
    CommandeFournisseur,
    Fournisseur,
    LigneCommandeFournisseur,
    MouvementDetteFournisseur,
    Produit,
    Unite,
)


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'couleur', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['name']


@admin.register(Unite)
class UniteAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbole', 'company', 'is_active']
    list_filter = ['company', 'is_active']


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'company', 'telephone', 'solde_dette', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['nom', 'code']


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ['reference', 'nom', 'company', 'categorie', 'prix_vente', 'is_active']
    list_filter = ['company', 'categorie', 'is_active', 'est_perimable']
    search_fields = ['nom', 'reference']


class LigneCommandeFournisseurInline(admin.TabularInline):
    model = LigneCommandeFournisseur
    extra = 0


@admin.register(CommandeFournisseur)
class CommandeFournisseurAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fournisseur', 'statut',
                    'date_livraison_prevue', 'created_par', 'created_at']
    list_filter = ['statut', 'fournisseur__company']
    readonly_fields = ['numero', 'created_at']
    inlines = [LigneCommandeFournisseurInline]


@admin.register(MouvementDetteFournisseur)
class MouvementDetteFournisseurAdmin(admin.ModelAdmin):
    list_display = ['fournisseur', 'type_mouvement', 'montant',
                    'reference', 'created_par', 'created_at']
    list_filter = ['type_mouvement', 'fournisseur__company']
    readonly_fields = ['created_at']
