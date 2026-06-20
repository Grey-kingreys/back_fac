from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Company(models.Model):

    class SubscriptionPlan(models.TextChoices):
        FREE = 'free', 'Gratuit'
        STARTER = 'starter', 'Starter'
        PRO = 'pro', 'Pro'
        ENTERPRISE = 'enterprise', 'Entreprise'

    name = models.CharField(max_length=255, unique=True, verbose_name="Nom")
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="Slug")
    logo = models.ImageField(upload_to='companies/logos/', null=True, blank=True, verbose_name="Logo")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    subscription_plan = models.CharField(
        max_length=20,
        choices=SubscriptionPlan.choices,
        default=SubscriptionPlan.FREE,
        verbose_name="Plan d'abonnement"
    )
    settings = models.JSONField(default=dict, blank=True, verbose_name="Paramètres")
    rayon_presence_m = models.PositiveIntegerField(
        default=100,
        verbose_name="Rayon de pointage présence (mètres)",
        help_text=(
            "Distance maximale autour du dépôt (ou du point central de la zone) "
            "pour qu'un pointage de présence soit considéré « dans le périmètre »."
        ),
    )

    class Meta:
        verbose_name = "Entreprise"
        verbose_name_plural = "Entreprises"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Zone(models.Model):
    """
    Zone géographique rattachée à une Company.
    Une Company possède plusieurs Zones.
    """
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="zones",
        verbose_name=_("Entreprise"),
    )
    name = models.CharField(_("Nom"), max_length=150)
    code = models.CharField(_("Code"), max_length=30)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Actif"), default=True)

    # ── Coordonnées GPS du point central de la zone ──────────────────────────
    latitude = models.DecimalField(
        _("Latitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude du point central de la zone (ex: 9.537500)",
    )
    longitude = models.DecimalField(
        _("Longitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude du point central de la zone (ex: -13.677300)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Zone")
        verbose_name_plural = _("Zones")
        ordering = ["company", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_zone_name_per_company",
            ),
            models.UniqueConstraint(
                fields=["company", "code"],
                name="unique_zone_code_per_company",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Depot(models.Model):
    """
    Dépôt physique rattaché à une Zone.
    Le gestionnaire est un utilisateur avec role=gestionnaire_stock affecté à ce dépôt
    via son champ User.depot (pas de FK inverse sur le modèle Depot).
    """
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name="depots",
        verbose_name=_("Zone"),
    )
    name = models.CharField(_("Nom"), max_length=150)
    code = models.CharField(_("Code"), max_length=30)
    address = models.TextField(_("Adresse"), blank=True)
    is_active = models.BooleanField(_("Actif"), default=True)

    # ── Coordonnées GPS propres au dépôt (marqueur à l'intérieur de sa zone) ─
    latitude = models.DecimalField(
        _("Latitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude du dépôt (ex: 9.537500)",
    )
    longitude = models.DecimalField(
        _("Longitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude du dépôt (ex: -13.677300)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Dépôt")
        verbose_name_plural = _("Dépôts")
        ordering = ["zone", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "name"],
                name="unique_depot_name_per_zone",
            ),
            models.UniqueConstraint(
                fields=["zone", "code"],
                name="unique_depot_code_per_zone",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name} ({self.zone.code})"

    @property
    def company(self):
        """Raccourci pratique pour accéder à la company via la zone."""
        return self.zone.company
