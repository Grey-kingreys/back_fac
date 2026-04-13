"""
apps/accounts/serializers.py
R1-B07 — Serializers CRUD Utilisateurs
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers

from apps.companies.models import Depot

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour la liste paginée des utilisateurs.
    Inclut les noms lisibles de company et depot.
    """
    company_name = serializers.CharField(source='company.name', read_only=True, default=None)
    depot_name = serializers.CharField(source='depot.name', read_only=True, default=None)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'role',
            'is_active',
            'company_id',
            'company_name',
            'depot_id',
            'depot_name',
            'created_at',
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le détail d'un utilisateur.
    """
    company_name = serializers.CharField(source='company.name', read_only=True, default=None)
    depot_name = serializers.CharField(source='depot.name', read_only=True, default=None)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'phone',
            'role',
            'is_active',
            'company_id',
            'company_name',
            'depot_id',
            'depot_name',
            'avatar_url',
            'failed_attempts',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'company_id', 'company_name', 'failed_attempts',
            'created_at', 'updated_at', 'avatar_url',
        ]

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer de création d'un utilisateur (Admin uniquement).
    Le mot de passe temporaire est obligatoire à la création.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    depot_id = serializers.PrimaryKeyRelatedField(
        queryset=Depot.objects.all(),
        source='depot',
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'phone',
            'role',
            'depot_id',
            'password',
        ]

    def validate_email(self, value):
        """Email unique par company."""
        request = self.context.get('request')
        company = request.user.company if request else None

        qs = User.objects.filter(email=value)
        if company:
            qs = qs.filter(company=company)

        if qs.exists():
            raise serializers.ValidationError(
                "Un utilisateur avec cet email existe déjà dans cette entreprise."
            )
        return value

    def validate_depot_id(self, depot):
        """Le dépôt doit appartenir à la même company que le créateur."""
        request = self.context.get('request')
        if depot and request and request.user.company:
            if depot.zone.company != request.user.company:
                raise serializers.ValidationError(
                    "Ce dépôt n'appartient pas à votre entreprise."
                )
        return depot

    def create(self, validated_data):
        request = self.context.get('request')
        password = validated_data.pop('password')

        # Rattacher automatiquement à la company du créateur
        if request and request.user.company:
            validated_data['company'] = request.user.company

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer de modification partielle d'un utilisateur (PATCH).
    L'email et la company ne sont pas modifiables ici.
    """
    depot_id = serializers.PrimaryKeyRelatedField(
        queryset=Depot.objects.all(),
        source='depot',
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'phone',
            'role',
            'is_active',
            'depot_id',
        ]

    def validate_depot_id(self, depot):
        """Le dépôt doit appartenir à la même company."""
        request = self.context.get('request')
        if depot and request and request.user.company:
            if depot.zone.company != request.user.company:
                raise serializers.ValidationError(
                    "Ce dépôt n'appartient pas à votre entreprise."
                )
        return depot


class AdminPasswordResetSerializer(serializers.Serializer):
    """
    Serializer pour le reset de mot de passe par un admin.
    """
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {'new_password_confirm': "Les mots de passe ne correspondent pas."}
            )
        return attrs
