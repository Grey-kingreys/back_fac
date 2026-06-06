"""
apps/logistique/serializers.py
"""

from rest_framework import serializers

from .models import LigneMission, Mission, PositionGPS, Vehicule


class VehiculeSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_vehicule_display', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    chauffeur_nom = serializers.CharField(
        source='chauffeur_attitré.get_full_name', read_only=True)

    class Meta:
        model = Vehicule
        fields = [
            'id', 'immatriculation', 'type_vehicule', 'type_label',
            'marque', 'modele', 'capacite_kg', 'statut', 'statut_label',
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
    vehicule_immat = serializers.CharField(
        source='vehicule.immatriculation', read_only=True)
    chauffeur_nom = serializers.CharField(
        source='chauffeur.get_full_name', read_only=True)
    depot_depart_nom = serializers.CharField(source='depot_depart.nom', read_only=True)
    depot_arrivee_nom = serializers.CharField(source='depot_arrivee.nom', read_only=True)

    class Meta:
        model = Mission
        fields = [
            'id', 'numero', 'statut', 'statut_label',
            'vehicule', 'vehicule_immat',
            'chauffeur', 'chauffeur_nom',
            'depot_depart', 'depot_depart_nom',
            'depot_arrivee', 'depot_arrivee_nom',
            'date_depart_prevue', 'date_depart_reelle', 'date_arrivee_reelle',
            'created_at',
        ]
        read_only_fields = fields


class MissionDetailSerializer(serializers.ModelSerializer):
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    vehicule_immat = serializers.CharField(
        source='vehicule.immatriculation', read_only=True)
    chauffeur_nom = serializers.CharField(
        source='chauffeur.get_full_name', read_only=True)
    depot_depart_nom = serializers.CharField(source='depot_depart.nom', read_only=True)
    depot_arrivee_nom = serializers.CharField(source='depot_arrivee.nom', read_only=True)
    lignes = LigneMissionSerializer(many=True, read_only=True)
    derniere_position = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            'id', 'numero', 'statut', 'statut_label',
            'vehicule', 'vehicule_immat',
            'chauffeur', 'chauffeur_nom',
            'depot_depart', 'depot_depart_nom',
            'depot_arrivee', 'depot_arrivee_nom',
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
    depot_depart = serializers.IntegerField()
    depot_arrivee = serializers.IntegerField()
    date_depart_prevue = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    lignes = LigneMissionInputSerializer(many=True, required=False)
    transfert_stock = serializers.IntegerField(required=False, allow_null=True)


class SignatureArriveeSerializer(serializers.Serializer):
    signature = serializers.CharField(
        help_text="Canvas HTML5 encodé en base64")
    quantites_recues = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="[{ligne_id: N, quantite_recue: X}]",
    )
    motif_litige = serializers.CharField(required=False, allow_blank=True)
