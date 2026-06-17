"""
apps/stocks/serializers.py
"""

from rest_framework import serializers

from .models import (
    AjustementStock,
    Inventaire,
    LigneInventaire,
    LigneTransfert,
    LotStock,
    MouvementStock,
    StockDepot,
    TransfertStock,
)


class StockDepotSerializer(serializers.ModelSerializer):
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    unite_symbole = serializers.CharField(source='produit.unite.symbole', read_only=True)
    depot_code = serializers.CharField(source='depot.code', read_only=True)
    depot_nom = serializers.CharField(source='depot.name', read_only=True)
    zone_nom = serializers.CharField(source='depot.zone.name', read_only=True)
    en_alerte = serializers.BooleanField(read_only=True)
    seuil_alerte = serializers.DecimalField(
        source='produit.seuil_alerte', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = StockDepot
        fields = [
            'id', 'depot', 'depot_code', 'depot_nom', 'zone_nom',
            'produit', 'produit_reference', 'produit_nom', 'unite_symbole',
            'quantite', 'seuil_alerte', 'en_alerte', 'updated_at',
        ]
        read_only_fields = fields


class LotStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = LotStock
        fields = ['id', 'stock_depot', 'numero_lot', 'quantite',
                  'date_fabrication', 'date_expiration', 'created_at']
        read_only_fields = ['id', 'created_at']


class MouvementStockSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_mouvement_display', read_only=True)
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    depot_code = serializers.CharField(source='depot.code', read_only=True)
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)

    class Meta:
        model = MouvementStock
        fields = [
            'id', 'depot', 'depot_code', 'produit', 'produit_reference', 'produit_nom',
            'type_mouvement', 'type_label', 'quantite',
            'quantite_avant', 'quantite_apres',
            'reference_doc', 'motif',
            'transfert', 'utilisateur', 'utilisateur_nom',
            'created_at',
        ]
        read_only_fields = fields


class EntreeStockSerializer(serializers.Serializer):
    """Saisie d'une entrée de stock manuelle (approvisionnement fournisseur)."""
    depot = serializers.PrimaryKeyRelatedField(
        queryset=__import__('apps.companies.models', fromlist=['Depot']).Depot.objects.all()
    )
    produit = serializers.PrimaryKeyRelatedField(
        queryset=__import__('apps.produits.models', fromlist=['Produit']).Produit.objects.all()
    )
    quantite = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0.001)
    numero_lot = serializers.CharField(max_length=100, required=False, allow_blank=True)
    date_expiration = serializers.DateField(required=False, allow_null=True)
    reference_doc = serializers.CharField(max_length=100, required=False, allow_blank=True)
    motif = serializers.CharField(required=False, allow_blank=True)


class SortieStockSerializer(serializers.Serializer):
    """Saisie d'une sortie de stock manuelle."""
    depot = serializers.PrimaryKeyRelatedField(
        queryset=__import__('apps.companies.models', fromlist=['Depot']).Depot.objects.all()
    )
    produit = serializers.PrimaryKeyRelatedField(
        queryset=__import__('apps.produits.models', fromlist=['Produit']).Produit.objects.all()
    )
    quantite = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0.001)
    reference_doc = serializers.CharField(max_length=100, required=False, allow_blank=True)
    motif = serializers.CharField(required=False, allow_blank=True)


# ── Transferts ────────────────────────────────────────────────────────────────
class LigneTransfertSerializer(serializers.ModelSerializer):
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)

    class Meta:
        model = LigneTransfert
        fields = ['id', 'produit', 'produit_reference', 'produit_nom',
                  'quantite_envoyee', 'quantite_recue', 'notes']


class LigneTransfertCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneTransfert
        fields = ['produit', 'quantite_envoyee', 'notes']


class TransfertListSerializer(serializers.ModelSerializer):
    depot_source_code = serializers.CharField(source='depot_source.code', read_only=True)
    depot_destination_code = serializers.CharField(source='depot_destination.code', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    nb_lignes = serializers.SerializerMethodField()

    class Meta:
        model = TransfertStock
        fields = [
            'id', 'numero', 'depot_source', 'depot_source_code',
            'depot_destination', 'depot_destination_code',
            'statut', 'statut_label', 'nb_lignes',
            'date_envoi', 'date_reception', 'created_at',
        ]
        read_only_fields = fields

    def get_nb_lignes(self, obj):
        return obj.lignes.count()


class TransfertDetailSerializer(serializers.ModelSerializer):
    lignes = LigneTransfertSerializer(many=True, read_only=True)
    depot_source_code = serializers.CharField(source='depot_source.code', read_only=True)
    depot_source_nom = serializers.CharField(source='depot_source.name', read_only=True)
    depot_destination_code = serializers.CharField(source='depot_destination.code', read_only=True)
    depot_destination_nom = serializers.CharField(source='depot_destination.name', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = TransfertStock
        fields = [
            'id', 'numero', 'statut', 'statut_label',
            'depot_source', 'depot_source_code', 'depot_source_nom',
            'depot_destination', 'depot_destination_code', 'depot_destination_nom',
            'lignes', 'notes',
            'date_envoi', 'date_reception',
            'utilisateur_envoi', 'utilisateur_reception',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'numero', 'statut_label',
            'depot_source_code', 'depot_source_nom',
            'depot_destination_code', 'depot_destination_nom',
            'date_envoi', 'date_reception',
            'utilisateur_envoi', 'utilisateur_reception',
            'created_at', 'updated_at',
        ]


class TransfertCreateSerializer(serializers.Serializer):
    """Création d'un transfert avec ses lignes."""
    depot_source = serializers.PrimaryKeyRelatedField(
        queryset=__import__('apps.companies.models', fromlist=['Depot']).Depot.objects.all()
    )
    depot_destination = serializers.PrimaryKeyRelatedField(
        queryset=__import__('apps.companies.models', fromlist=['Depot']).Depot.objects.all()
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    lignes = LigneTransfertCreateSerializer(many=True)

    def validate(self, data):
        if data['depot_source'] == data['depot_destination']:
            raise serializers.ValidationError(
                "Le dépôt source et destination doivent être différents.")
        if not data.get('lignes'):
            raise serializers.ValidationError(
                {'lignes': "Au moins une ligne est requise."})
        return data


class ReceptionTransfertSerializer(serializers.Serializer):
    """Saisie des quantités reçues pour chaque ligne."""
    lignes = serializers.ListField(
        child=serializers.DictField(child=serializers.DecimalField(
            max_digits=12, decimal_places=3))
    )


# ── Inventaires ───────────────────────────────────────────────────────────────
class LigneInventaireSerializer(serializers.ModelSerializer):
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    ecart = serializers.DecimalField(
        max_digits=12, decimal_places=3, read_only=True, allow_null=True)

    class Meta:
        model = LigneInventaire
        fields = ['id', 'produit', 'produit_reference', 'produit_nom',
                  'quantite_theorique', 'quantite_comptee', 'ecart']
        read_only_fields = ['id', 'produit_reference', 'produit_nom',
                            'quantite_theorique', 'ecart']


class InventaireListSerializer(serializers.ModelSerializer):
    depot_code = serializers.CharField(source='depot.code', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    nb_lignes = serializers.SerializerMethodField()

    class Meta:
        model = Inventaire
        fields = ['id', 'numero', 'depot', 'depot_code', 'statut', 'statut_label',
                  'nb_lignes', 'created_at', 'valide_le']
        read_only_fields = fields

    def get_nb_lignes(self, obj):
        return obj.lignes.count()


class InventaireDetailSerializer(serializers.ModelSerializer):
    depot_nom = serializers.CharField(source='depot.name', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    cree_par_nom = serializers.CharField(source='cree_par.get_full_name', read_only=True)
    lignes = LigneInventaireSerializer(many=True, read_only=True)

    class Meta:
        model = Inventaire
        fields = ['id', 'numero', 'depot', 'depot_nom', 'statut', 'statut_label',
                  'notes', 'lignes', 'cree_par', 'cree_par_nom',
                  'created_at', 'valide_le']
        read_only_fields = fields


class InventaireCreateSerializer(serializers.Serializer):
    depot = serializers.PrimaryKeyRelatedField(
        queryset=__import__('apps.companies.models', fromlist=['Depot']).Depot.objects.all()
    )
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class ValiderInventaireSerializer(serializers.Serializer):
    lignes = serializers.ListField(
        child=serializers.DictField(),
        help_text="[{ligne_id: int, quantite_comptee: decimal}, ...]",
    )


# ── Ajustements de stock ──────────────────────────────────────────────────────
class AjustementStockSerializer(serializers.ModelSerializer):
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    depot_code = serializers.CharField(source='depot.code', read_only=True)
    demande_par_nom = serializers.CharField(source='demande_par.get_full_name', read_only=True)

    class Meta:
        model = AjustementStock
        fields = ['id', 'depot', 'depot_code', 'produit', 'produit_nom',
                  'quantite', 'motif', 'statut', 'statut_label',
                  'demande_par', 'demande_par_nom', 'traite_par',
                  'created_at', 'traite_le']
        read_only_fields = ['id', 'statut_label', 'produit_nom', 'depot_code',
                            'demande_par', 'demande_par_nom', 'traite_par',
                            'statut', 'created_at', 'traite_le']
