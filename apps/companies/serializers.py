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
    """
    Serializer léger pour la liste des zones.
    Inclut le nombre de dépôts et les coordonnées GPS.
    """
    depot_count = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = [
            'id',
            'name',
            'code',
            'description',
            'is_active',
            'latitude',
            'longitude',
            'depot_count',
            'created_at',
        ]
        read_only_fields = fields

    def get_depot_count(self, obj):
        return obj.depots.count()


class ZoneDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet avec la liste des dépôts imbriqués et les coordonnées GPS.
    Utilisé pour GET /api/zones/{id}/ et les réponses de création/modification.
    """
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
            'latitude',
            'longitude',
            'depot_count',
            'depots',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'depot_count', 'depots']

    def get_depot_count(self, obj):
        return obj.depots.count()

    def get_depots(self, obj):
        return DepotListSerializer(obj.depots.all(), many=True).data


class ZoneCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer de création et modification d'une zone.
    Les coordonnées GPS sont optionnelles — elles peuvent être définies
    plus tard via un clic sur la carte OpenStreetMap (frontend).
    """

    class Meta:
        model = Zone
        fields = [
            'name',
            'code',
            'description',
            'is_active',
            'latitude',
            'longitude',
        ]

    def validate_code(self, value):
        """Code unique globalement (insensible à la casse). Stocké en majuscules."""
        qs = Zone.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Ce code est déjà utilisé par une autre zone."
            )
        return value.upper()

    def validate_latitude(self, value):
        """Latitude doit être entre -90 et 90."""
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError(
                "La latitude doit être comprise entre -90 et 90."
            )
        return value

    def validate_longitude(self, value):
        """Longitude doit être entre -180 et 180."""
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError(
                "La longitude doit être comprise entre -180 et 180."
            )
        return value

    def validate(self, attrs):
        """Nom unique par company."""
        request = self.context.get('request')
        company = request.user.company if request else None

        if company and 'name' in attrs:
            qs = Zone.objects.filter(company=company, name__iexact=attrs['name'])
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
    """
    Serializer léger pour la liste des dépôts.
    Utilisé aussi pour les dépôts imbriqués dans ZoneDetailSerializer.
    """
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
    """
    Serializer complet d'un dépôt.
    Inclut les coordonnées GPS de la zone parente — utile pour
    le frontend qui doit positionner le marqueur sur la carte.
    """
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    zone_code = serializers.CharField(source='zone.code', read_only=True)
    zone_latitude = serializers.DecimalField(
        source='zone.latitude', max_digits=9, decimal_places=6, read_only=True
    )
    zone_longitude = serializers.DecimalField(
        source='zone.longitude', max_digits=9, decimal_places=6, read_only=True
    )

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
            'zone_latitude',
            'zone_longitude',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DepotCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer de création et modification d'un dépôt.
    La zone doit appartenir à la même company que l'utilisateur connecté.
    """
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
        """Code unique globalement (insensible à la casse). Stocké en majuscules."""
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
