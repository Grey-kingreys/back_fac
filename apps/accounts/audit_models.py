# apps/accounts/audit_models.py
"""
R1-B09 — Modèles AuditLog et LoginLog
Traçabilité complète des actions utilisateurs et des tentatives de connexion.
"""

from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Enregistre chaque create/update/delete sur les modèles sensibles.
    Alimenté par les signaux Django (signals.py).
    Immuable après création — aucune modification possible.
    """

    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Utilisateur"
    )

    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        verbose_name="Action"
    )

    model_name = models.CharField(
        max_length=100,
        verbose_name="Modèle concerné",
        help_text="Nom de la classe du modèle (ex: CustomUser, Zone, Depot)"
    )

    object_id = models.PositiveIntegerField(
        verbose_name="ID de l'objet"
    )

    data_before = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Données avant modification"
    )

    data_after = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Données après modification"
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Horodatage"
    )

    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', '-timestamp']),
        ]

    def __str__(self):
        user_str = str(self.user) if self.user else "Système"
        return f"[{self.get_action_display()}] {self.model_name}#{self.object_id} par {user_str}"


class LoginLog(models.Model):
    """
    Enregistre chaque tentative de connexion (succès et échec).
    Alimenté par LoginLogMiddleware (middleware.py).
    Immuable après création.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_logs',
        verbose_name="Utilisateur",
        help_text="Null si l'email n'existe pas dans la base"
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )

    user_agent = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="User-Agent (navigateur)"
    )

    success = models.BooleanField(
        verbose_name="Connexion réussie"
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Horodatage"
    )

    class Meta:
        verbose_name = "Journal de connexion"
        verbose_name_plural = "Journaux de connexion"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]

    def __str__(self):
        statut = "✓" if self.success else "✗"
        user_str = str(self.user) if self.user else "inconnu"
        return f"[{statut}] {user_str} — {self.timestamp:%Y-%m-%d %H:%M}"