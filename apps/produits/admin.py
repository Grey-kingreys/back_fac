from django.contrib import admin

from .models import Categorie, Fournisseur, Produit, Unite


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
