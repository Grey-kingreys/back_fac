"""
apps/ventes/serializers.py
"""

from rest_framework import serializers

from apps.companies.models import Depot

from .models import (
    Client,
    Commande,
    Devis,
    HistoriquePoints,
    LigneCommande,
    LigneDevis,
    LigneRetour,
    Paiement,
    ParametresFidelite,
    Promotion,
    RetourCommande,
)


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

    def validate(self, attrs):
        MODES_MOBILE = {Paiement.Mode.ORANGE_MONEY, Paiement.Mode.MTN_MONEY, Paiement.Mode.VIREMENT}
        if attrs.get('mode_paiement_initial') in MODES_MOBILE and not attrs.get('reference_paiement', '').strip():
            raise serializers.ValidationError(
                {'reference_paiement': "La référence de transaction est obligatoire pour ce mode de paiement."}
            )
        return attrs


class PaiementInputSerializer(serializers.Serializer):
    """Ajout d'un paiement sur une commande existante."""
    montant = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    mode = serializers.ChoiceField(choices=Paiement.Mode.choices)
    reference = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        MODES_MOBILE = {Paiement.Mode.ORANGE_MONEY, Paiement.Mode.MTN_MONEY, Paiement.Mode.VIREMENT}
        if attrs.get('mode') in MODES_MOBILE and not attrs.get('reference', '').strip():
            raise serializers.ValidationError(
                {'reference': "La référence de transaction est obligatoire pour ce mode de paiement."}
            )
        return attrs


# ── Historique points ─────────────────────────────────────────────────────────
class HistoriquePointsSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_mouvement_display', read_only=True)
    client_nom = serializers.CharField(source='client.nom_complet', read_only=True)

    class Meta:
        model = HistoriquePoints
        fields = ['id', 'client', 'client_nom', 'type_mouvement', 'type_label',
                  'points', 'commande', 'note', 'created_at']
        read_only_fields = fields


# ── Devis ─────────────────────────────────────────────────────────────────────
class LigneDevisSerializer(serializers.ModelSerializer):
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    montant_ht = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = LigneDevis
        fields = ['id', 'produit', 'produit_reference', 'produit_nom',
                  'quantite', 'prix_unitaire_ht', 'montant_ht']


class LigneDevisCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneDevis
        fields = ['produit', 'quantite', 'prix_unitaire_ht']


class DevisListSerializer(serializers.ModelSerializer):
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    client_nom = serializers.SerializerMethodField()
    nb_lignes = serializers.SerializerMethodField()

    class Meta:
        model = Devis
        fields = ['id', 'numero', 'statut', 'statut_label',
                  'client', 'client_nom', 'depot',
                  'date_expiration', 'nb_lignes', 'created_at']
        read_only_fields = fields

    def get_client_nom(self, obj):
        return obj.client.nom_complet if obj.client else "Anonyme"

    def get_nb_lignes(self, obj):
        return obj.lignes.count()


class DevisDetailSerializer(serializers.ModelSerializer):
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    client_nom = serializers.SerializerMethodField()
    lignes = LigneDevisSerializer(many=True, read_only=True)
    cree_par_nom = serializers.CharField(source='cree_par.get_full_name', read_only=True)

    class Meta:
        model = Devis
        fields = ['id', 'numero', 'statut', 'statut_label',
                  'client', 'client_nom', 'depot', 'commande',
                  'date_expiration', 'notes', 'lignes',
                  'cree_par', 'cree_par_nom', 'created_at', 'updated_at']
        read_only_fields = ['id', 'numero', 'statut_label', 'client_nom',
                            'commande', 'cree_par', 'cree_par_nom',
                            'created_at', 'updated_at']

    def get_client_nom(self, obj):
        return obj.client.nom_complet if obj.client else "Anonyme"


class DevisCreateSerializer(serializers.Serializer):
    depot = serializers.PrimaryKeyRelatedField(
        queryset=Depot.objects.all()
    )
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=False, allow_null=True,
    )
    date_expiration = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    lignes = LigneDevisCreateSerializer(many=True)

    def validate_lignes(self, value):
        if not value:
            raise serializers.ValidationError("Au moins une ligne est requise.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        company = request.user.company if request else None
        if company:
            depot = attrs.get('depot')
            if depot and depot.zone.company != company:
                raise serializers.ValidationError(
                    {'depot': "Ce dépôt n'appartient pas à votre entreprise."}
                )
            client = attrs.get('client')
            if client and client.company != company:
                raise serializers.ValidationError(
                    {'client': "Ce client n'appartient pas à votre entreprise."}
                )
        return attrs


# ── Retours commandes ─────────────────────────────────────────────────────────
class LigneRetourSerializer(serializers.ModelSerializer):
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)

    class Meta:
        model = LigneRetour
        fields = ['id', 'produit', 'produit_reference', 'produit_nom',
                  'quantite', 'motif_ligne']


class LigneRetourCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneRetour
        fields = ['produit', 'quantite', 'motif_ligne']


class RetourCommandeSerializer(serializers.ModelSerializer):
    motif_label = serializers.CharField(source='get_motif_display', read_only=True)
    type_retour_label = serializers.CharField(
        source='get_type_retour_display', read_only=True)
    lignes = LigneRetourSerializer(many=True, read_only=True)
    traite_par_nom = serializers.CharField(
        source='traite_par.get_full_name', read_only=True)

    class Meta:
        model = RetourCommande
        fields = ['id', 'commande', 'motif', 'motif_label',
                  'type_retour', 'type_retour_label',
                  'montant_rembourse', 'notes', 'lignes',
                  'traite_par', 'traite_par_nom', 'created_at']
        read_only_fields = ['id', 'motif_label', 'type_retour_label',
                            'traite_par', 'traite_par_nom', 'created_at']


class RetourCommandeCreateSerializer(serializers.Serializer):
    commande = serializers.PrimaryKeyRelatedField(
        queryset=Commande.objects.all()
    )
    motif = serializers.ChoiceField(choices=RetourCommande.Motif.choices)
    type_retour = serializers.ChoiceField(choices=RetourCommande.TypeRetour.choices)
    montant_rembourse = serializers.DecimalField(
        max_digits=14, decimal_places=2, default=0, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)
    lignes = LigneRetourCreateSerializer(many=True)

    def validate_lignes(self, value):
        if not value:
            raise serializers.ValidationError("Au moins une ligne est requise.")
        return value

    def validate_commande(self, commande):
        request = self.context.get('request')
        company = request.user.company if request else None
        if company and commande.company != company:
            raise serializers.ValidationError(
                "Cette commande n'appartient pas à votre entreprise."
            )
        return commande


# ── Promotions ────────────────────────────────────────────────────────────────
class PromotionSerializer(serializers.ModelSerializer):
    est_active_aujourd_hui = serializers.ReadOnlyField()

    class Meta:
        model = Promotion
        fields = [
            'id', 'nom', 'type_promotion', 'valeur', 'cible',
            'client', 'categorie', 'produit',
            'date_debut', 'date_fin', 'is_active',
            'est_active_aujourd_hui', 'created_by', 'created_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'est_active_aujourd_hui']

    def validate(self, attrs):
        request = self.context.get('request')
        company = request.user.company if request else None
        if company:
            client = attrs.get('client')
            if client and client.company != company:
                raise serializers.ValidationError(
                    {'client': "Ce client n'appartient pas à votre entreprise."}
                )
            categorie = attrs.get('categorie')
            if categorie and categorie.company != company:
                raise serializers.ValidationError(
                    {'categorie': "Cette catégorie n'appartient pas à votre entreprise."}
                )
            produit = attrs.get('produit')
            if produit and produit.company != company:
                raise serializers.ValidationError(
                    {'produit': "Ce produit n'appartient pas à votre entreprise."}
                )
        return attrs
