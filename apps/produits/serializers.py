"""
apps/produits/serializers.py
"""

from rest_framework import serializers

from .models import (
    Categorie,
    CommandeFournisseur,
    EvaluationFournisseur,
    Fournisseur,
    LigneCommandeFournisseur,
    MouvementDetteFournisseur,
    Produit,
    Unite,
)


# ── Catégorie ─────────────────────────────────────────────────────────────────
class CategorieSerializer(serializers.ModelSerializer):
    nombre_produits = serializers.SerializerMethodField()

    class Meta:
        model = Categorie
        fields = ['id', 'name', 'description', 'couleur', 'tva_taux', 'is_active',
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


# ── Produit ───────────────────────────────────────────────────────────────────
class ProduitListSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.name', read_only=True)
    unite_symbole = serializers.CharField(source='unite.symbole', read_only=True)
    marge = serializers.FloatField(read_only=True)

    class Meta:
        model = Produit
        fields = ['id', 'reference', 'code_barre', 'nom', 'categorie_nom',
                  'unite_symbole', 'prix_achat', 'prix_vente', 'marge',
                  'seuil_alerte', 'est_perimable', 'is_active', 'created_at']
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
            'id', 'reference', 'code_barre', 'nom', 'description', 'image',
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


# ── Commandes fournisseurs ────────────────────────────────────────────────────
class LigneCommandeFournisseurSerializer(serializers.ModelSerializer):
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    montant_total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = LigneCommandeFournisseur
        fields = ['id', 'produit', 'produit_nom', 'produit_reference',
                  'quantite_commandee', 'prix_unitaire', 'quantite_recue', 'montant_total']
        read_only_fields = ['id', 'produit_nom', 'produit_reference',
                            'montant_total', 'quantite_recue']


class CommandeFournisseurListSerializer(serializers.ModelSerializer):
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = CommandeFournisseur
        fields = ['id', 'numero', 'fournisseur', 'fournisseur_nom',
                  'statut', 'statut_label', 'date_livraison_prevue', 'created_at']
        read_only_fields = fields


class CommandeFournisseurDetailSerializer(serializers.ModelSerializer):
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    depot_nom = serializers.CharField(source='depot_destination.name', read_only=True)
    lignes = LigneCommandeFournisseurSerializer(many=True, read_only=True)

    class Meta:
        model = CommandeFournisseur
        fields = ['id', 'numero', 'fournisseur', 'fournisseur_nom',
                  'statut', 'statut_label', 'depot_destination', 'depot_nom',
                  'date_livraison_prevue', 'notes', 'lignes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'numero', 'fournisseur_nom', 'statut_label',
                            'depot_nom', 'lignes', 'created_at', 'updated_at']


class LigneCommandeFournisseurCreateSerializer(serializers.Serializer):
    produit = serializers.PrimaryKeyRelatedField(queryset=Produit.objects.all())
    quantite_commandee = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=0.001)
    prix_unitaire = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=0)


class CommandeFournisseurCreateSerializer(serializers.ModelSerializer):
    lignes = LigneCommandeFournisseurCreateSerializer(many=True)

    class Meta:
        model = CommandeFournisseur
        fields = ['fournisseur', 'depot_destination', 'date_livraison_prevue', 'notes', 'lignes']

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes')
        validated_data['company'] = self.context['request'].user.company
        validated_data['created_par'] = self.context['request'].user
        commande = CommandeFournisseur.objects.create(**validated_data)
        for ligne in lignes_data:
            LigneCommandeFournisseur.objects.create(commande=commande, **ligne)
        return commande


class MouvementDetteFournisseurSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_mouvement_display', read_only=True)
    created_par_nom = serializers.CharField(source='created_par.get_full_name', read_only=True)

    class Meta:
        model = MouvementDetteFournisseur
        fields = ['id', 'fournisseur', 'type_mouvement', 'type_label',
                  'montant', 'reference', 'notes',
                  'created_par', 'created_par_nom', 'created_at']
        read_only_fields = ['id', 'type_label', 'created_par', 'created_par_nom', 'created_at']


# ── Évaluations fournisseurs ──────────────────────────────────────────────────
class EvaluationFournisseurSerializer(serializers.ModelSerializer):
    note_globale = serializers.ReadOnlyField()
    evalue_par_nom = serializers.CharField(source='evalue_par.get_full_name', read_only=True)
    fournisseur_nom = serializers.CharField(source='fournisseur.nom', read_only=True)

    class Meta:
        model = EvaluationFournisseur
        fields = [
            'id', 'fournisseur', 'fournisseur_nom', 'commande',
            'note_qualite', 'note_delai', 'note_service', 'note_globale',
            'commentaire', 'evalue_par', 'evalue_par_nom', 'created_at',
        ]
        read_only_fields = ['id', 'evalue_par', 'evalue_par_nom', 'note_globale', 'fournisseur_nom', 'created_at']
