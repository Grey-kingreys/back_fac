"""
apps/finance/serializers.py
"""

from rest_framework import serializers

from .models import (
    CaisseEntreprise,
    CaissePhysique,
    CaisseZone,
    CompteMobileMoney,
    ConfigurationCaisse,
    DepenseOperationnelle,
    SessionCaisse,
    TauxChange,
    TransactionCaisse,
    TransactionMobileMoney,
    VersementCaisse,
)


class ConfigurationCaisseSerializer(serializers.ModelSerializer):
    updated_by_nom = serializers.CharField(
        source='updated_by.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = ConfigurationCaisse
        fields = ['id', 'duree_session_jours', 'duree_caisse_depot_jours',
                  'duree_caisse_zone_jours', 'updated_at', 'updated_by', 'updated_by_nom']
        read_only_fields = ['id', 'updated_at', 'updated_by', 'updated_by_nom']

    def validate(self, attrs):
        # Valeurs effectives (fusion instance existante + payload partiel)
        def eff(field):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, None)

        session = eff('duree_session_jours')
        depot = eff('duree_caisse_depot_jours')
        zone = eff('duree_caisse_zone_jours')
        if None not in (session, depot, zone):
            if not (session < depot < zone):
                raise serializers.ValidationError(
                    "Les durées doivent être strictement croissantes : "
                    "session < dépôt < zone."
                )
        return attrs


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
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = CaissePhysique
        fields = ['id', 'nom', 'depot', 'depot_nom', 'devise', 'solde_actuel',
                  'statut', 'statut_label', 'is_active', 'created_at', 'fermee_le']
        read_only_fields = ['id', 'depot_nom', 'solde_actuel', 'statut', 'statut_label',
                            'is_active', 'created_at', 'fermee_le']

    def validate(self, attrs):
        # Au plus une caisse OUVERTE par dépôt (les fermées restent en base, §1).
        depot = attrs.get('depot')
        if self.instance is None and depot is not None:
            if CaissePhysique.objects.filter(
                depot=depot, statut=CaissePhysique.Statut.OUVERTE
            ).exists():
                raise serializers.ValidationError(
                    {'depot': "Ce dépôt a déjà une caisse ouverte. "
                              "Fermez-la avant d'en créer une nouvelle."}
                )
        return attrs

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
    fermee_par_nom = serializers.CharField(source='fermee_par.get_full_name', read_only=True, allow_null=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    nombre_transactions = serializers.SerializerMethodField()
    total_entrees = serializers.SerializerMethodField()
    total_sorties = serializers.SerializerMethodField()

    class Meta:
        model = SessionCaisse
        fields = ['id', 'caisse', 'caisse_nom', 'caissier', 'caissier_nom',
                  'statut', 'statut_label', 'solde_ouverture',
                  'solde_fermeture_theorique', 'solde_fermeture_reel',
                  'ecart', 'ouvert_le', 'ferme_le', 'fermee_par', 'fermee_par_nom',
                  'nombre_transactions', 'total_entrees', 'total_sorties']
        read_only_fields = fields

    def get_nombre_transactions(self, obj):
        return obj.transactions.count()

    def get_total_entrees(self, obj):
        from django.db.models import Sum
        result = obj.transactions.filter(
            type_transaction__in=['entree', 'vente', 'approvisionnement', 'remboursement']
        ).aggregate(total=Sum('montant'))['total']
        return result or 0

    def get_total_sorties(self, obj):
        from django.db.models import Sum
        result = obj.transactions.filter(
            type_transaction__in=['sortie', 'retrait']
        ).aggregate(total=Sum('montant'))['total']
        return result or 0


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

    def validate(self, attrs):
        # Le motif est obligatoire si un écart est détecté — pré-validation au niveau serializer
        # La validation définitive reste dans SessionCaisse.fermer() (modèle)
        # mais on rend motif_ecart required=True quand l'écart sera calculé
        return attrs


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
    reference_operateur = serializers.CharField()
    reference_doc = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)


# ── Hiérarchie caisses ────────────────────────────────────────────────────────
class CaisseZoneSerializer(serializers.ModelSerializer):
    zone_nom = serializers.CharField(source='zone.name', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = CaisseZone
        fields = ['id', 'nom', 'zone', 'zone_nom', 'devise',
                  'solde_actuel', 'statut', 'statut_label', 'is_active', 'created_at', 'fermee_le']
        read_only_fields = ['id', 'zone_nom', 'solde_actuel', 'statut', 'statut_label',
                            'is_active', 'created_at', 'fermee_le']

    def validate(self, attrs):
        # Au plus une caisse zone OUVERTE par zone (les fermées restent en base, §1).
        zone = attrs.get('zone')
        if self.instance is None and zone is not None:
            if CaisseZone.objects.filter(
                zone=zone, statut=CaisseZone.Statut.OUVERTE
            ).exists():
                raise serializers.ValidationError(
                    {'zone': "Cette zone a déjà une caisse ouverte. "
                             "Fermez-la avant d'en créer une nouvelle."}
                )
        return attrs

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

    def validate(self, attrs):
        if not attrs.get('justificatif') and not (self.instance and self.instance.justificatif):
            raise serializers.ValidationError(
                {'justificatif': "Un justificatif est obligatoire pour tout versement inter-niveau."}
            )
        # Règle universelle §4 : double comptage obligatoire à la création
        montant_receveur = attrs.get('montant_comptage_receveur')
        if self.instance is None and montant_receveur is None:
            raise serializers.ValidationError(
                {'montant_comptage_receveur': "Le montant du receveur est obligatoire (double comptage §4)."}
            )
        # Règle universelle §2 : tout écart au double comptage exige un motif
        montant = attrs.get('montant')
        if montant_receveur is not None and montant is not None:
            if montant_receveur != montant and not attrs.get('motif_ecart'):
                raise serializers.ValidationError(
                    {'motif_ecart': "Un motif est obligatoire lorsque le comptage du receveur diffère du montant versé."}
                )
        return attrs


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
