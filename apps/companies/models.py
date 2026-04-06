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
    code = models.CharField(_("Code"), max_length=30, unique=True)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Actif"), default=True)
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
            )
        ]
 
    def __str__(self):
        return f"{self.code} — {self.name}"
 
 
class Depot(models.Model):
    """
    Dépôt physique rattaché à une Zone.
    Chaque dépôt aura sa propre caisse et ses propres stocks (releases futures).
    """
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name="depots",
        verbose_name=_("Zone"),
    )
    name = models.CharField(_("Nom"), max_length=150)
    code = models.CharField(_("Code"), max_length=30, unique=True)
    address = models.TextField(_("Adresse"), blank=True)
    is_active = models.BooleanField(_("Actif"), default=True)
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
            )
        ]
 
    def __str__(self):
        return f"{self.code} — {self.name} ({self.zone.code})"
 
    @property
    def company(self):
        """Raccourci pratique pour accéder à la company via la zone."""
        return self.zone.company
