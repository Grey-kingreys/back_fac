"""
apps/accounts/models.py
Modèle utilisateur personnalisé avec rôles et multi-entreprises.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models


# ---------------------------------------------------------------------------
# Enum des rôles
# ---------------------------------------------------------------------------
class Role(models.TextChoices):
    SUPERADMIN = 'superadmin', 'Super Administrateur'
    ADMIN = 'admin', 'Administrateur'
    SUPERVISEUR = 'superviseur', 'Superviseur'
    GESTIONNAIRE_STOCK = 'gestionnaire_stock', 'Gestionnaire de Stock'
    CAISSIER = 'caissier', 'Caissier'
    CHAUFFEUR = 'chauffeur', 'Chauffeur'
    MAINTENANCIER = 'maintenancier', 'Maintenancier'
    COMMERCIAL = 'commercial', 'Commercial'


# ---------------------------------------------------------------------------
# Manager personnalisé
# ---------------------------------------------------------------------------
class CustomUserManager(BaseUserManager):
    """
    Manager qui utilise l'email comme identifiant unique
    au lieu du username Django par défaut.
    """

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', Role.SUPERADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Le superuser doit avoir is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Le superuser doit avoir is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


# ---------------------------------------------------------------------------
# Modèle CustomUser
# ---------------------------------------------------------------------------
class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Utilisateur personnalisé.
    - Connexion par email (pas de username)
    - Appartient obligatoirement à une Company (sauf le superadmin)
    - Peut être rattaché à un Dépôt (optionnel)
    - Son rôle détermine ses permissions dans toute l'app
    """

    # ── Identification ──────────────────────────────────────────────────────
    email = models.EmailField(unique=True, verbose_name="Email")
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")

    # ── Rattachement organisationnel ────────────────────────────────────────
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='users',
        verbose_name="Entreprise",
        null=True,
        blank=True,
    )

    # ── CORRIGÉ R1-B08 : depot pointe maintenant sur companies.Depot ────────
    depot = models.ForeignKey(
        'companies.Depot',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="Dépôt",
    )

    # ── Rôle ─────────────────────────────────────────────────────────────────
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.COMMERCIAL,
        verbose_name="Rôle",
    )

    # ── Avatar ────────────────────────────────────────────────────────────────
    avatar = models.ImageField(
        upload_to='accounts/avatars/',
        null=True,
        blank=True,
        verbose_name="Avatar",
    )

    # ── Sécurité ──────────────────────────────────────────────────────────────
    failed_attempts = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Tentatives de connexion échouées",
    )

    # ── Flags Django standard ─────────────────────────────────────────────────
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_staff = models.BooleanField(default=False, verbose_name="Staff admin")

    # ── Métadonnées ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    # ── Configuration manager + champ de login ─────────────────────────────────
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['last_name', 'first_name']

    # ── Méthodes utilitaires ───────────────────────────────────────────────────
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}> [{self.get_role_display()}]"

    @property
    def is_superadmin(self):
        return self.role == Role.SUPERADMIN

    @property
    def is_admin_or_above(self):
        return self.role in (Role.SUPERADMIN, Role.ADMIN)

    def reset_failed_attempts(self):
        if self.failed_attempts > 0:
            self.failed_attempts = 0
            self.save(update_fields=['failed_attempts'])

    def increment_failed_attempts(self):
        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            self.is_active = False
            self.save(update_fields=['failed_attempts', 'is_active'])
        else:
            self.save(update_fields=['failed_attempts'])

    def clean(self):
        if self.role == Role.SUPERADMIN:
            if self.company_id is not None:
                raise ValidationError("Le Super Administrateur ne doit pas être rattaché à une entreprise.")
        else:
            if self.company_id is None:
                raise ValidationError("Un utilisateur doit appartenir à une entreprise.")

        # Le dépôt doit appartenir à la même company que l'utilisateur
        if self.depot_id and self.company_id:
            if self.depot.zone.company_id != self.company_id:
                raise ValidationError(
                    "Le dépôt doit appartenir à la même entreprise que l'utilisateur."
                )
