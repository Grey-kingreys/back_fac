"""
apps/accounts/admin.py
Interface d'administration pour CustomUser.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    On hérite de UserAdmin (qui gère déjà bien le hash de mot de passe,
    les formulaires de changement de MDP, etc.) et on surcharge
    les champs pour coller à notre modèle sans username.
    """

    # ── Colonnes dans la liste ─────────────────────────────────────────────
    list_display = ('email', 'first_name', 'last_name', 'company', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'company')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('last_name', 'first_name')

    # ── Formulaire d'édition (détail) ─────────────────────────────────────
    fieldsets = (
        (_('Connexion'), {
            'fields': ('email', 'password')
        }),
        (_('Informations personnelles'), {
            'fields': ('first_name', 'last_name', 'phone', 'avatar')
        }),
        (_('Organisation'), {
            'fields': ('company', 'depot', 'role')
        }),
        (_('Sécurité'), {
            'fields': ('failed_attempts',),
            'classes': ('collapse',),
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Métadonnées'), {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'failed_attempts')

    # ── Formulaire de création (depuis l'admin) ────────────────────────────
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'company', 'role', 'password1', 'password2'),
        }),
    )

    # UserAdmin s'attend à un champ `username` — on le désactive
    filter_horizontal = ('groups', 'user_permissions')
