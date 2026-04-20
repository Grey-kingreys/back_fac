# apps/companies/serializers_company.py
"""
Serializers pour le CRUD Company — SuperAdmin uniquement.
"""

from rest_framework import serializers

from .models import Company


class CompanyListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour la liste des companies.
    """
    nombre_utilisateurs = serializers.SerializerMethodField()
    nombre_zones = serializers.SerializerMethodField()
    statut = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id',
            'name',
            'slug',
            'logo',
            'is_active',
            'statut',
            'subscription_plan',
            'nombre_utilisateurs',
            'nombre_zones',
            'created_at',
        ]
        read_only_fields = fields

    def get_nombre_utilisateurs(self, obj):
        return obj.users.filter(is_active=True).count()

    def get_nombre_zones(self, obj):
        return obj.zones.count()

    def get_statut(self, obj):
        return 'active' if obj.is_active else 'suspendue'


class CompanyDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le détail d'une company.
    Utilisé aussi par l'Admin pour voir/modifier sa propre company.
    """
    nombre_utilisateurs = serializers.SerializerMethodField()
    nombre_zones = serializers.SerializerMethodField()
    nombre_depots = serializers.SerializerMethodField()
    statut = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id',
            'name',
            'slug',
            'logo',
            'is_active',
            'statut',
            'subscription_plan',
            'settings',
            'nombre_utilisateurs',
            'nombre_zones',
            'nombre_depots',
            'created_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'is_active']

    def get_nombre_utilisateurs(self, obj):
        return obj.users.filter(is_active=True).count()

    def get_nombre_zones(self, obj):
        return obj.zones.count()

    def get_nombre_depots(self, obj):
        from .models import Depot
        return Depot.objects.filter(zone__company=obj).count()

    def get_statut(self, obj):
        return 'active' if obj.is_active else 'suspendue'


class CompanyCreateSerializer(serializers.ModelSerializer):
    """
    Création d'une company par le SuperAdmin.

    En un seul appel :
    - La company est créée
    - Un utilisateur Admin est créé avec l'email fourni
    - Un email est envoyé à l'Admin avec un lien de première connexion
      contenant un token UUID usage unique (sans expiration)
    """
    email_admin = serializers.EmailField(write_only=True)

    class Meta:
        model = Company
        fields = [
            'name',
            'email_admin',
            'subscription_plan',
            'settings',
        ]

    def validate_name(self, value):
        value = value.strip()
        if Company.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                "Une entreprise avec ce nom existe déjà."
            )
        return value

    def validate_email_admin(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Un utilisateur avec cet email existe déjà."
            )
        return value

    def create(self, validated_data):
        import uuid

        from django.contrib.auth import get_user_model
        from django.db import transaction

        from .services import send_first_login_email

        email_admin = validated_data.pop('email_admin')
        User = get_user_model()

        with transaction.atomic():
            # 1. Créer la company
            company = Company.objects.create(**validated_data)

            # 2. Créer l'utilisateur Admin
            admin_user = User.objects.create_user(
                email=email_admin,
                password=None,  # pas de mot de passe — défini via le lien
                role='admin',
                company=company,
                is_active=False,  # inactif jusqu'à la première connexion
                first_login_token=uuid.uuid4(),
                first_login_done=False,
            )

            # 3. Envoyer l'email avec le lien de première connexion
            email_ok = send_first_login_email(admin_user, company)
            if not email_ok:
                import logging
                logging.getLogger(__name__).warning(
                    f"[FirstLogin] Email non envoyé pour {email_admin}"
                )

        # Stocker pour la réponse
        company._admin_email = email_admin
        company._email_envoye = email_ok
        return company

    def to_representation(self, instance):
        data = CompanyDetailSerializer(instance, context=self.context).data
        data['admin'] = {
            'email': getattr(instance, '_admin_email', None),
            'email_envoye': getattr(instance, '_email_envoye', False),
        }
        return data


class CompanyUpdateSerializer(serializers.ModelSerializer):
    """
    Modification partielle d'une company.
    Utilisé par le SuperAdmin ET par l'Admin pour sa propre company.
    L'Admin peut modifier : name, logo, subscription_plan, settings.
    Le SuperAdmin peut en plus activer/suspendre via l'endpoint toggle.
    """

    class Meta:
        model = Company
        fields = [
            'name',
            'logo',
            'subscription_plan',
            'settings',
        ]

    def validate_name(self, value):
        value = value.strip()
        qs = Company.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Une entreprise avec ce nom existe déjà."
            )
        return value

    def to_representation(self, instance):
        return CompanyDetailSerializer(instance, context=self.context).data
