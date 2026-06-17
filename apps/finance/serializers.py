"""
apps/finance/serializers.py
"""

from rest_framework import serializers

from .models import (
    CaisseEntreprise,
    CaissePhysique,
    CaisseZone,
    CompteMobileMoney,
    DepenseOperationnelle,
    SessionCaisse,
    TauxChange,
    TransactionCaisse,
    TransactionMobileMoney,
    VersementCaisse,
)


class TauxChangeSerializer(serializers.ModelSerializer):
    est_expire = serializers.BooleanField(read_only=True)
    created_by_nom = serializers.CharField(
        source='created_by.get_full_name', read_only=True)

    class Meta:
        model = TauxChange
        fields = ['id', 'devise_source', 'devise_cible', 'taux',
                  'date_expiration', 'est_expire', 'created_by', 'created_by_nom',
                  'created_at']
        read_only_fields = ['id', 'est_expire', 'created_by', 'created_by_nom', 'created_at']

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CaissePhysiqueSerializer(serializers.ModelSerializer):
    depot_nom = serializers.CharField(source='depot.name', read_only=True)

    class Meta:
        model = CaissePhysique
        fields = ['id', 'nom', 'depot', 'depot_nom', 'solde_actuel', 'is_active', 'created_at']
        read_only_fields = ['id', 'depot_nom', 'solde_actuel', 'created_at']

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


class TransactionCaisseSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_transaction_display', read_only=True)
    created_by_nom = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = TransactionCaisse
        fields = ['id', 'type_transaction', 'type_label', 'montant',
                  'reference_doc', 'description', 'created_by', 'created_by_nom',
                  'created_at']
        read_only_fields = ['id', 'type_label', 'created_by', 'created_by_nom', 'created_at']


class TransactionCaisseInputSerializer(serializers.Serializer):
    type_transaction = serializers.ChoiceField(
        choices=TransactionCaisse.TypeTransaction.choices)
    montant = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    reference_doc = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)


class SessionCaisseListSerializer(serializers.ModelSerializer):
    caisse_nom = serializers.CharField(source='caisse.nom', read_only=True)
    caissier_nom = serializers.CharField(source='caissier.get_full_name', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = SessionCaisse
        fields = ['id', 'caisse', 'caisse_nom', 'caissier', 'caissier_nom',
                  'statut', 'statut_label', 'solde_ouverture',
                  'solde_fermeture_theorique', 'solde_fermeture_reel',
                  'ecart', 'ouvert_le', 'ferme_le']
        read_only_fields = fields


class SessionCaisseDetailSerializer(serializers.ModelSerializer):
    caisse_nom = serializers.CharField(source='caisse.nom', read_only=True)
    caissier_nom = serializers.CharField(source='caissier.get_full_name', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    transactions = TransactionCaisseSerializer(many=True, read_only=True)

    class Meta:
        model = SessionCaisse
        fields = ['id', 'caisse', 'caisse_nom', 'caissier', 'caissier_nom',
                  'statut', 'statut_label', 'solde_ouverture',
                  'solde_fermeture_theorique', 'solde_fermeture_reel',
                  'ecart', 'motif_ecart', 'notes',
                  'ouvert_le', 'ferme_le', 'transactions']
        read_only_fields = fields


class OuvrirSessionSerializer(serializers.Serializer):
    caisse = serializers.IntegerField()
    solde_ouverture = serializers.DecimalField(
        max_digits=16, decimal_places=2, min_value=0, default=0)
    notes = serializers.CharField(required=False, allow_blank=True)


class FermerSessionSerializer(serializers.Serializer):
    solde_reel = serializers.DecimalField(max_digits=16, decimal_places=2, min_value=0)
    motif_ecart = serializers.CharField(required=False, allow_blank=True)


# ── Mobile Money ──────────────────────────────────────────────────────────────
class CompteMobileMoneySerializer(serializers.ModelSerializer):
    operateur_label = serializers.CharField(source='get_operateur_display', read_only=True)
    depot_nom = serializers.CharField(source='depot.name', read_only=True)

    class Meta:
        model = CompteMobileMoney
        fields = ['id', 'operateur', 'operateur_label', 'depot', 'depot_nom',
                  'numero', 'nom_titulaire', 'solde', 'is_active', 'created_at']
        read_only_fields = ['id', 'operateur_label', 'depot_nom', 'solde', 'created_at']

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


class TransactionMobileMoneySerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_transaction_display', read_only=True)
    created_by_nom = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = TransactionMobileMoney
        fields = ['id', 'compte', 'type_transaction', 'type_label', 'montant',
                  'reference_operateur', 'reference_doc', 'description',
                  'created_by', 'created_by_nom', 'created_at']
        read_only_fields = ['id', 'type_label', 'created_by', 'created_by_nom', 'created_at']


class TransactionMobileMoneyInputSerializer(serializers.Serializer):
    type_transaction = serializers.ChoiceField(
        choices=TransactionMobileMoney.TypeTransaction.choices)
    montant = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    reference_operateur = serializers.CharField(required=False, allow_blank=True)
    reference_doc = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)


# ── Hiérarchie caisses ────────────────────────────────────────────────────────
class CaisseZoneSerializer(serializers.ModelSerializer):
    zone_nom = serializers.CharField(source='zone.name', read_only=True)

    class Meta:
        model = CaisseZone
        fields = ['id', 'nom', 'zone', 'zone_nom', 'devise',
                  'solde_actuel', 'is_active', 'created_at']
        read_only_fields = ['id', 'zone_nom', 'solde_actuel', 'created_at']

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


class CaisseEntrepriseSerializer(serializers.ModelSerializer):
    company_nom = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = CaisseEntreprise
        fields = ['id', 'nom', 'company', 'company_nom', 'devise',
                  'solde_actuel', 'is_active', 'created_at']
        read_only_fields = ['id', 'company', 'company_nom', 'solde_actuel', 'created_at']


class VersementCaisseSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_versement_display', read_only=True)
    effectue_par_nom = serializers.CharField(source='effectue_par.get_full_name', read_only=True)
    recu_par_nom = serializers.CharField(source='recu_par.get_full_name', read_only=True)
    ecart = serializers.DecimalField(
        max_digits=16, decimal_places=2, read_only=True, allow_null=True)

    class Meta:
        model = VersementCaisse
        fields = [
            'id', 'type_versement', 'type_label',
            'caisse_source_depot', 'caisse_source_zone',
            'caisse_dest_zone', 'caisse_dest_entreprise',
            'montant', 'justificatif', 'montant_comptage_receveur',
            'ecart', 'motif_ecart',
            'effectue_par', 'effectue_par_nom', 'recu_par', 'recu_par_nom',
            'created_at',
        ]
        read_only_fields = ['id', 'type_label', 'ecart',
                            'effectue_par', 'effectue_par_nom',
                            'recu_par_nom', 'created_at']


class DepenseOperationnelleSerializer(serializers.ModelSerializer):
    enregistre_par_nom = serializers.CharField(source='enregistre_par.get_full_name', read_only=True)
    depot_nom = serializers.CharField(source='depot.name', read_only=True, allow_null=True)

    class Meta:
        model = DepenseOperationnelle
        fields = [
            'id', 'company', 'depot', 'depot_nom', 'categorie',
            'montant', 'description', 'date_depense', 'reference',
            'justificatif', 'enregistre_par', 'enregistre_par_nom',
            'session_caisse', 'created_at',
        ]
        read_only_fields = ['id', 'company', 'enregistre_par', 'enregistre_par_nom', 'depot_nom', 'created_at']
