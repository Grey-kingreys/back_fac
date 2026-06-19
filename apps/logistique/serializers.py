"""
apps/logistique/serializers.py
"""

from rest_framework import serializers

from .models import (
    ConsommationCarburant,
    DocumentVehicule,
    LigneMission,
    Maintenance,
    Mission,
    Panne,
    PositionGPS,
    Vehicule,
)


class VehiculeSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_vehicule_display', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    chauffeur_nom = serializers.CharField(
        source='chauffeur_attitré.get_full_name', read_only=True)

    class Meta:
        model = Vehicule
        fields = [
            'id', 'immatriculation', 'type_vehicule', 'type_label',
            'marque', 'modele', 'annee', 'capacite_kg', 'kilometrage_actuel',
            'statut', 'statut_label',
            'chauffeur_attitré', 'chauffeur_nom',
            'has_nfc', 'nfc_tag', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'type_label', 'statut_label', 'chauffeur_nom', 'created_at']

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


class LigneMissionSerializer(serializers.ModelSerializer):
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)

    class Meta:
        model = LigneMission
        fields = ['id', 'produit', 'produit_nom', 'produit_reference',
                  'quantite', 'quantite_recue', 'observations']
        read_only_fields = ['id', 'produit_nom', 'produit_reference']


class LigneMissionInputSerializer(serializers.Serializer):
    produit = serializers.IntegerField()
    quantite = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0.001)


class PositionGPSSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionGPS
        fields = ['id', 'latitude', 'longitude', 'vitesse_kmh', 'enregistre_le']
        read_only_fields = ['id', 'enregistre_le']


class MissionListSerializer(serializers.ModelSerializer):
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    type_label = serializers.CharField(source='get_type_mission_display', read_only=True)
    vehicule_immat = serializers.CharField(
        source='vehicule.immatriculation', read_only=True)
    chauffeur_nom = serializers.CharField(
        source='chauffeur.get_full_name', read_only=True)
    depot_depart_nom = serializers.CharField(source='depot_depart.name', read_only=True, default=None)
    depot_arrivee_nom = serializers.CharField(source='depot_arrivee.name', read_only=True, default=None)
    client_nom = serializers.SerializerMethodField()
    fournisseur_nom = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            'id', 'numero', 'statut', 'statut_label',
            'type_mission', 'type_label',
            'vehicule', 'vehicule_immat',
            'chauffeur', 'chauffeur_nom',
            'depot_depart', 'depot_depart_nom',
            'depot_arrivee', 'depot_arrivee_nom',
            'client', 'client_nom',
            'fournisseur', 'fournisseur_nom',
            'date_depart_prevue', 'date_depart_reelle', 'date_arrivee_reelle',
            'created_at',
        ]
        read_only_fields = fields

    def get_client_nom(self, obj):
        return str(obj.client) if obj.client_id else None

    def get_fournisseur_nom(self, obj):
        return obj.fournisseur.nom if obj.fournisseur_id else None


class MissionDetailSerializer(serializers.ModelSerializer):
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    type_label = serializers.CharField(source='get_type_mission_display', read_only=True)
    vehicule_immat = serializers.CharField(
        source='vehicule.immatriculation', read_only=True)
    chauffeur_nom = serializers.CharField(
        source='chauffeur.get_full_name', read_only=True)
    depot_depart_nom = serializers.CharField(source='depot_depart.name', read_only=True, default=None)
    depot_arrivee_nom = serializers.CharField(source='depot_arrivee.name', read_only=True, default=None)
    client_nom = serializers.SerializerMethodField()
    fournisseur_nom = serializers.SerializerMethodField()
    lignes = LigneMissionSerializer(many=True, read_only=True)
    derniere_position = serializers.SerializerMethodField()

    def get_client_nom(self, obj):
        return str(obj.client) if obj.client_id else None

    def get_fournisseur_nom(self, obj):
        return obj.fournisseur.nom if obj.fournisseur_id else None

    class Meta:
        model = Mission
        fields = [
            'id', 'numero', 'statut', 'statut_label',
            'type_mission', 'type_label',
            'vehicule', 'vehicule_immat',
            'chauffeur', 'chauffeur_nom',
            'depot_depart', 'depot_depart_nom',
            'depot_arrivee', 'depot_arrivee_nom',
            'client', 'client_nom',
            'fournisseur', 'fournisseur_nom',
            'transfert_stock', 'date_depart_prevue',
            'date_depart_reelle', 'date_arrivee_reelle',
            'notes', 'motif_litige', 'signature_arrivee',
            'lignes', 'derniere_position',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'numero', 'statut_label', 'vehicule_immat', 'chauffeur_nom',
            'depot_depart_nom', 'depot_arrivee_nom', 'derniere_position',
            'created_at', 'updated_at',
        ]

    def get_derniere_position(self, obj):
        pos = obj.positions.order_by('-enregistre_le').first()
        if pos:
            return PositionGPSSerializer(pos).data
        return None


class MissionCreateSerializer(serializers.Serializer):
    vehicule = serializers.IntegerField()
    chauffeur = serializers.IntegerField()
    # Dépôts/Client/Fournisseur : requis selon le type (voir validate()).
    depot_depart = serializers.IntegerField(required=False, allow_null=True)
    depot_arrivee = serializers.IntegerField(required=False, allow_null=True)
    client = serializers.IntegerField(required=False, allow_null=True)
    fournisseur = serializers.IntegerField(required=False, allow_null=True)
    type_mission = serializers.ChoiceField(
        choices=Mission.TypeMission.choices,
        default=Mission.TypeMission.TRANSFERT,
    )
    date_depart_prevue = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    lignes = LigneMissionInputSerializer(many=True, required=False)
    transfert_stock = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        """Champs requis selon le type de mission :
        - transfert  : dépôt départ + dépôt arrivée
        - livraison  : dépôt départ (source) + client
        - enlevement : fournisseur + dépôt arrivée (destination)
        """
        t = attrs.get('type_mission', Mission.TypeMission.TRANSFERT)
        errors = {}
        if t == Mission.TypeMission.TRANSFERT:
            if not attrs.get('depot_depart'):
                errors['depot_depart'] = "Dépôt de départ requis pour un transfert."
            if not attrs.get('depot_arrivee'):
                errors['depot_arrivee'] = "Dépôt d'arrivée requis pour un transfert."
        elif t == Mission.TypeMission.LIVRAISON:
            if not attrs.get('depot_depart'):
                errors['depot_depart'] = "Dépôt source requis pour une livraison."
            if not attrs.get('client'):
                errors['client'] = "Client requis pour une livraison."
        elif t == Mission.TypeMission.ENLEVEMENT:
            if not attrs.get('fournisseur'):
                errors['fournisseur'] = "Fournisseur requis pour un enlèvement."
            if not attrs.get('depot_arrivee'):
                errors['depot_arrivee'] = "Dépôt d'arrivée requis pour un enlèvement."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class SignatureArriveeSerializer(serializers.Serializer):
    signature = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Canvas HTML5 encodé en base64. Vide si refus_signature=true.",
    )
    refus_signature = serializers.BooleanField(
        default=False,
        help_text="True si le destinataire refuse de signer → statut LITIGE immédiat.",
    )
    quantites_recues = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="[{ligne_id: N, quantite_recue: X}]",
    )
    motif_litige = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('refus_signature') and not attrs.get('signature'):
            raise serializers.ValidationError(
                {'signature': "La signature est obligatoire (sauf si refus_signature=true)."}
            )
        return attrs


# ── Maintenance ───────────────────────────────────────────────────────────────
class MaintenanceSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(
        source='get_type_maintenance_display', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    vehicule_immat = serializers.CharField(
        source='vehicule.immatriculation', read_only=True)
    effectue_par_nom = serializers.CharField(
        source='effectue_par.get_full_name', read_only=True)

    class Meta:
        model = Maintenance
        fields = [
            'id', 'vehicule', 'vehicule_immat',
            'type_maintenance', 'type_label',
            'description', 'kilometrage_au_moment', 'cout',
            'statut', 'statut_label',
            'date_planifiee', 'date_reelle',
            'effectue_par', 'effectue_par_nom',
            'notes', 'created_at',
        ]
        read_only_fields = ['id', 'type_label', 'statut_label',
                            'vehicule_immat', 'effectue_par_nom', 'created_at']


# ── Pannes ────────────────────────────────────────────────────────────────────
class PanneSerializer(serializers.ModelSerializer):
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    vehicule_immat = serializers.CharField(
        source='vehicule.immatriculation', read_only=True)
    declare_par_nom = serializers.CharField(
        source='declare_par.get_full_name', read_only=True)

    class Meta:
        model = Panne
        fields = [
            'id', 'vehicule', 'vehicule_immat',
            'description', 'date_declaration',
            'mission', 'cout_reparation',
            'statut', 'statut_label',
            'declare_par', 'declare_par_nom', 'resolu_le',
        ]
        read_only_fields = ['id', 'statut_label', 'vehicule_immat',
                            'declare_par', 'declare_par_nom',
                            'date_declaration', 'resolu_le']


# ── Documents véhicule ────────────────────────────────────────────────────────
class DocumentVehiculeSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_document_display', read_only=True)
    vehicule_immat = serializers.CharField(
        source='vehicule.immatriculation', read_only=True)
    is_expire = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentVehicule
        fields = [
            'id', 'vehicule', 'vehicule_immat',
            'type_document', 'type_label',
            'fichier', 'date_expiration', 'is_expire',
            'notes', 'created_at',
        ]
        read_only_fields = ['id', 'type_label', 'vehicule_immat',
                            'is_expire', 'created_at']


# ── Consommation carburant ────────────────────────────────────────────────────
class ConsommationCarburantSerializer(serializers.ModelSerializer):
    montant_total = serializers.ReadOnlyField()
    vehicule_immat = serializers.CharField(source='vehicule.immatriculation', read_only=True)

    class Meta:
        model = ConsommationCarburant
        fields = [
            'id', 'vehicule', 'vehicule_immat', 'mission',
            'type_carburant', 'quantite_litres', 'prix_par_litre',
            'montant_total', 'kilometrage', 'date_plein',
            'station', 'enregistre_par', 'created_at',
        ]
        read_only_fields = ['id', 'enregistre_par', 'montant_total', 'vehicule_immat', 'created_at']
