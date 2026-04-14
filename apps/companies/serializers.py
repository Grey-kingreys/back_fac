"""
apps/companies/serializers.py
R1-B08 — Serializers CRUD Zones et Dépôts
"""

from rest_framework import serializers

from .models import Depot, Zone

# ─────────────────────────────────────────────────────────────────────────────
# ZONE
# ─────────────────────────────────────────────────────────────────────────────


class ZoneListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des zones."""
    depot_count = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = [
            'id',
            'name',
            'code',
            'description',
            'is_active',
            'depot_count',
            'created_at',
        ]
        read_only_fields = fields

    def get_depot_count(self, obj):
        return obj.depots.count()


class ZoneDetailSerializer(serializers.ModelSerializer):
    """Serializer complet avec la liste des dépôts imbriqués."""
    depots = serializers.SerializerMethodField()
    depot_count = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = [
            'id',
            'name',
            'code',
            'description',
            'is_active',
            'depot_count',
            'depots',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'depot_count', 'depots']

    def get_depot_count(self, obj):
        return obj.depots.count()

    def get_depots(self, obj):
        # Retourne les dépôts imbriqués (léger, sans récursion)
        return DepotListSerializer(obj.depots.all(), many=True).data


class ZoneCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer de création et modification d'une zone."""

    class Meta:
        model = Zone
        fields = [
            'name',
            'code',
            'description',
            'is_active',
        ]

    def validate_code(self, value):
        """Code unique globalement (contrainte DB), on donne un message clair."""
        qs = Zone.objects.filter(code__iexact=value)
        # En modification, exclure l'instance courante
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ce code est déjà utilisé par une autre zone.")
        return value.upper()

    def validate(self, attrs):
        """Nom unique par company."""
        request = self.context.get('request')
        company = request.user.company if request else None

        if company:
            qs = Zone.objects.filter(company=company, name__iexact=attrs.get('name', ''))
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'name': "Une zone avec ce nom existe déjà dans votre entreprise."}
                )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.company:
            validated_data['company'] = request.user.company
        return Zone.objects.create(**validated_data)


# ─────────────────────────────────────────────────────────────────────────────
# DÉPÔT
# ─────────────────────────────────────────────────────────────────────────────

class DepotListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des dépôts."""
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    zone_code = serializers.CharField(source='zone.code', read_only=True)

    class Meta:
        model = Depot
        fields = [
            'id',
            'name',
            'code',
            'address',
            'is_active',
            'zone_id',
            'zone_name',
            'zone_code',
            'created_at',
        ]
        read_only_fields = fields


class DepotDetailSerializer(serializers.ModelSerializer):
    """Serializer complet d'un dépôt."""
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    zone_code = serializers.CharField(source='zone.code', read_only=True)

    class Meta:
        model = Depot
        fields = [
            'id',
            'name',
            'code',
            'address',
            'is_active',
            'zone_id',
            'zone_name',
            'zone_code',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DepotCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer de création et modification d'un dépôt."""
    zone_id = serializers.PrimaryKeyRelatedField(
        queryset=Zone.objects.filter(is_active=True),
        source='zone',
    )

    class Meta:
        model = Depot
        fields = [
            'name',
            'code',
            'address',
            'is_active',
            'zone_id',
        ]

    def validate_zone_id(self, zone):
        """La zone doit appartenir à la company de l'utilisateur connecté."""
        request = self.context.get('request')
        if request and request.user.company:
            if zone.company != request.user.company:
                raise serializers.ValidationError(
                    "Cette zone n'appartient pas à votre entreprise."
                )
        return zone

    def validate_code(self, value):
        """Code unique globalement."""
        qs = Depot.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ce code est déjà utilisé par un autre dépôt.")
        return value.upper()

    def validate(self, attrs):
        """Nom unique par zone."""
        zone = attrs.get('zone', self.instance.zone if self.instance else None)
        name = attrs.get('name', self.instance.name if self.instance else '')

        if zone and name:
            qs = Depot.objects.filter(zone=zone, name__iexact=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'name': "Un dépôt avec ce nom existe déjà dans cette zone."}
                )
        return attrs
