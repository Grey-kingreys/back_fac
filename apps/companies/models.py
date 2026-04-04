from django.db import models
from django.utils.text import slugify


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