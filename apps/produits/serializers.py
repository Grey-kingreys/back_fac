"""
apps/produits/serializers.py
"""

from rest_framework import serializers

from .models import Categorie, Fournisseur, Produit, Unite


# ── Catégorie ─────────────────────────────────────────────────────────────────
class CategorieSerializer(serializers.ModelSerializer):
    nombre_produits = serializers.SerializerMethodField()

    class Meta:
        model = Categorie
        fields = ['id', 'name', 'description', 'couleur', 'is_active',
                  'nombre_produits', 'created_at']
        read_only_fields = ['id', 'nombre_produits', 'created_at']

    def get_nombre_produits(self, obj):
        return obj.produits.filter(is_active=True).count()

    def validate_name(self, value):
        company = self.context['request'].user.company
        qs = Categorie.objects.filter(company=company, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Une catégorie avec ce nom existe déjà.")
        return value

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


# ── Unité ────────────────────────────────────────────────────────────────────
class UniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unite
        fields = ['id', 'name', 'symbole', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_symbole(self, value):
        company = self.context['request'].user.company
        qs = Unite.objects.filter(company=company, symbole__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Une unité avec ce symbole existe déjà.")
        return value

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


# ── Fournisseur ──────────────────────────────────────────────────────────────
class FournisseurListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fournisseur
        fields = ['id', 'code', 'nom', 'telephone', 'email',
                  'solde_dette', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


# ── FournisseurDetail ─────────────────────────────────────────────────────────
class FournisseurDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fournisseur
        fields = ['id', 'code', 'nom', 'telephone', 'email', 'adresse',
                  'solde_dette', 'notes', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_code(self, value):
        company = self.context['request'].user.company
        qs = Fournisseur.objects.filter(company=company, code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Un fournisseur avec ce code existe déjà.")
        return value.upper()

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


# ── Produit ──────────────────────────────────────────────────────────────────
class ProduitListSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.name', read_only=True)
    unite_symbole = serializers.CharField(source='unite.symbole', read_only=True)
    marge = serializers.FloatField(read_only=True)

    class Meta:
        model = Produit
        fields = ['id', 'reference', 'nom', 'categorie_nom', 'unite_symbole',
                  'prix_achat', 'prix_vente', 'marge', 'seuil_alerte',
                  'est_perimable', 'is_active', 'created_at']
        read_only_fields = fields


# ── ProduitDetail ─────────────────────────────────────────────────────────────
class ProduitDetailSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.name', read_only=True)
    unite_nom = serializers.CharField(source='unite.name', read_only=True)
    unite_symbole = serializers.CharField(source='unite.symbole', read_only=True)
    fournisseur_nom = serializers.CharField(
        source='fournisseur_principal.nom', read_only=True, default=None)
    marge = serializers.FloatField(read_only=True)

    class Meta:
        model = Produit
        fields = [
            'id', 'reference', 'nom', 'description', 'image',
            'categorie', 'categorie_nom',
            'unite', 'unite_nom', 'unite_symbole',
            'fournisseur_principal', 'fournisseur_nom',
            'prix_achat', 'prix_vente', 'marge', 'tva_taux',
            'seuil_alerte', 'seuil_max',
            'est_perimable', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'categorie_nom', 'unite_nom', 'unite_symbole',
                            'fournisseur_nom', 'marge', 'created_at', 'updated_at']

    def validate_reference(self, value):
        company = self.context['request'].user.company
        qs = Produit.objects.filter(company=company, reference__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Un produit avec cette référence existe déjà.")
        return value.upper()

    def validate(self, data):
        company = self.context['request'].user.company
        categorie = data.get('categorie', getattr(self.instance, 'categorie', None))
        unite = data.get('unite', getattr(self.instance, 'unite', None))
        fournisseur = data.get('fournisseur_principal',
                               getattr(self.instance, 'fournisseur_principal', None))
        if categorie and categorie.company != company:
            raise serializers.ValidationError(
                {'categorie': "Cette catégorie n'appartient pas à votre entreprise."})
        if unite and unite.company != company:
            raise serializers.ValidationError(
                {'unite': "Cette unité n'appartient pas à votre entreprise."})
        if fournisseur and fournisseur.company != company:
            raise serializers.ValidationError(
                {'fournisseur_principal': "Ce fournisseur n'appartient pas à votre entreprise."})
        return data

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)
