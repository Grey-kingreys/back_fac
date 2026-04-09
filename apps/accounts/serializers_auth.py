"""
R1-B05 — Serializers d'authentification
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers

User = get_user_model()


# ── Serializers utilitaires (pour la doc Swagger) ─────────────────────────────

class MessageSerializer(serializers.Serializer):
    """Réponse simple avec un message texte."""
    detail = serializers.CharField()


class TokenRefreshSerializer(serializers.Serializer):
    """Corps de requête contenant un refresh token."""
    refresh = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    """Réponse du login : access + refresh + infos user."""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.DictField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class MeSerializer(serializers.ModelSerializer):
    """
    Profil complet de l'utilisateur connecté.
    Retourne les infos nécessaires pour que le frontend adapte l'interface.
    """

    company_name = serializers.CharField(
        source="company.name", read_only=True, default=None
    )
    depot_name = serializers.CharField(
        source="depot.name", read_only=True, default=None
    )
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_active",
            "company_id",
            "company_name",
            "depot_id",
            "depot_name",
            "avatar_url",
        ]
        read_only_fields = fields

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Les mots de passe ne correspondent pas."}
            )
        # Validation Django (longueur, complexité, etc.)
        validate_password(attrs["new_password"])
        return attrs
