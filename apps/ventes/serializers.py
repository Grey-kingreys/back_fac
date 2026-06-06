"""
apps/ventes/serializers.py
"""

from rest_framework import serializers

from .models import Client, Commande, LigneCommande, Paiement, ParametresFidelite


class ParametresFideliteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParametresFidelite
        fields = ['id', 'is_active', 'tranche_montant',
                  'points_par_tranche', 'valeur_point_gnf']
        read_only_fields = ['id']


class ClientListSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)

    class Meta:
        model = Client
        fields = ['id', 'code', 'nom', 'prenom', 'nom_complet', 'telephone',
                  'points_fidelite', 'solde_credit', 'is_active', 'created_at']
        read_only_fields = fields


class ClientDetailSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)

    class Meta:
        model = Client
        fields = ['id', 'code', 'nom', 'prenom', 'nom_complet',
                  'telephone', 'email', 'adresse',
                  'points_fidelite', 'solde_credit',
                  'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'nom_complet', 'points_fidelite',
                            'solde_credit', 'created_at', 'updated_at']

    def validate_code(self, value):
        company = self.context['request'].user.company
        qs = Client.objects.filter(company=company, code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Un client avec ce code existe déjà.")
        return value.upper()

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


# ── Commandes ────────────────────────────────────────────────────────────────
class LigneCommandeSerializer(serializers.ModelSerializer):
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    unite_symbole = serializers.CharField(source='produit.unite.symbole', read_only=True)

    class Meta:
        model = LigneCommande
        fields = ['id', 'produit', 'produit_reference', 'produit_nom', 'unite_symbole',
                  'quantite', 'prix_unitaire_ht', 'tva_taux',
                  'montant_ht', 'montant_tva', 'montant_ttc']
        read_only_fields = ['id', 'produit_reference', 'produit_nom', 'unite_symbole',
                            'montant_ht', 'montant_tva', 'montant_ttc']


class LigneCommandeInputSerializer(serializers.Serializer):
    produit = serializers.IntegerField()
    quantite = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0.001)
    prix_unitaire_ht = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False)


class PaiementSerializer(serializers.ModelSerializer):
    mode_label = serializers.CharField(source='get_mode_display', read_only=True)
    caissier_nom = serializers.CharField(source='caissier.get_full_name', read_only=True)

    class Meta:
        model = Paiement
        fields = ['id', 'montant', 'mode', 'mode_label', 'reference',
                  'caissier', 'caissier_nom', 'created_at']
        read_only_fields = ['id', 'mode_label', 'caissier', 'caissier_nom', 'created_at']


class CommandeListSerializer(serializers.ModelSerializer):
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    client_nom = serializers.SerializerMethodField()
    nb_lignes = serializers.SerializerMethodField()
    reste_a_payer = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Commande
        fields = [
            'id', 'numero', 'statut', 'statut_label',
            'client', 'client_nom', 'depot',
            'montant_ttc', 'remise', 'montant_paye', 'reste_a_payer',
            'mode_paiement', 'nb_lignes', 'created_at',
        ]
        read_only_fields = fields

    def get_client_nom(self, obj):
        return obj.client.nom_complet if obj.client else "Anonyme"

    def get_nb_lignes(self, obj):
        return obj.lignes.count()


class CommandeDetailSerializer(serializers.ModelSerializer):
    lignes = LigneCommandeSerializer(many=True, read_only=True)
    paiements = PaiementSerializer(many=True, read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    mode_paiement_label = serializers.CharField(
        source='get_mode_paiement_display', read_only=True)
    client_nom = serializers.SerializerMethodField()
    caissier_nom = serializers.CharField(source='caissier.get_full_name', read_only=True)
    reste_a_payer = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True)
    est_solde = serializers.BooleanField(read_only=True)

    class Meta:
        model = Commande
        fields = [
            'id', 'numero', 'statut', 'statut_label',
            'client', 'client_nom', 'depot',
            'mode_paiement', 'mode_paiement_label',
            'montant_ht', 'tva_total', 'montant_ttc',
            'remise', 'montant_paye', 'reste_a_payer', 'est_solde',
            'points_utilises', 'points_gagnes',
            'notes', 'caissier', 'caissier_nom',
            'lignes', 'paiements',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'numero', 'statut_label', 'mode_paiement_label',
            'client_nom', 'caissier', 'caissier_nom',
            'montant_ht', 'tva_total', 'montant_ttc',
            'montant_paye', 'reste_a_payer', 'est_solde',
            'points_gagnes',
            'created_at', 'updated_at',
        ]

    def get_client_nom(self, obj):
        return obj.client.nom_complet if obj.client else "Anonyme"


class CommandeCreateSerializer(serializers.Serializer):
    """Création d'une commande avec ses lignes en un seul appel."""
    depot = serializers.IntegerField()
    client = serializers.IntegerField(required=False, allow_null=True)
    mode_paiement = serializers.ChoiceField(
        choices=Commande.ModePaiement.choices,
        default=Commande.ModePaiement.COMPTANT,
    )
    remise = serializers.DecimalField(
        max_digits=12, decimal_places=2, default=0, min_value=0)
    points_utilises = serializers.IntegerField(default=0, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)
    lignes = LigneCommandeInputSerializer(many=True)
    montant_paye = serializers.DecimalField(
        max_digits=14, decimal_places=2, default=0, min_value=0)
    mode_paiement_initial = serializers.ChoiceField(
        choices=Paiement.Mode.choices,
        required=False,
        default=Paiement.Mode.ESPECES,
    )
    reference_paiement = serializers.CharField(required=False, allow_blank=True)

    def validate_lignes(self, value):
        if not value:
            raise serializers.ValidationError("Au moins une ligne est requise.")
        return value


class PaiementInputSerializer(serializers.Serializer):
    """Ajout d'un paiement sur une commande existante."""
    montant = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    mode = serializers.ChoiceField(choices=Paiement.Mode.choices)
    reference = serializers.CharField(required=False, allow_blank=True)
