"""
apps/notifications/models.py
Notifications in-app pour tous les rôles.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):

    class TypeNotification(models.TextChoices):
        RUPTURE_STOCK = 'rupture_stock', _("Rupture de stock")
        SEUIL_STOCK = 'seuil_stock', _("Seuil de stock atteint")
        ECART_CAISSE = 'ecart_caisse', _("Écart de caisse")
        MISSION_LITIGE = 'mission_litige', _("Mission en litige")
        TAUX_CHANGE_EXPIRE = 'taux_change_expire', _("Taux de change expiré")
        ECHEANCE_CLIENT = 'echeance_client', _("Échéance client")
        TRANSFERT_VALIDE = 'transfert_valide', _("Transfert de stock reçu")
        CONGE_DEMANDE = 'conge_demande', _("Demande de congé")
        CONGE_APPROUVE = 'conge_approuve', _("Congé approuvé")
        CONGE_REJETE = 'conge_rejete', _("Congé refusé")
        MAINTENANCE_VEHICULE = 'maintenance_vehicule', _("Maintenance véhicule")
        COMMANDE_FOURNISSEUR = 'commande_fournisseur', _("Commande fournisseur")
        INFO = 'info', _("Information")

    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications', verbose_name=_("Destinataire"),
    )
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='notifications', verbose_name=_("Entreprise"),
    )
    type_notification = models.CharField(
        _("Type"), max_length=30, choices=TypeNotification.choices,
        default=TypeNotification.INFO,
    )
    titre = models.CharField(_("Titre"), max_length=200)
    message = models.TextField(_("Message"))
    lien = models.CharField(
        _("Lien"), max_length=300, blank=True,
        help_text="URL relative vers la ressource concernée",
    )
    est_lue = models.BooleanField(_("Lue"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_type_notification_display()}] {self.destinataire} — {self.titre}"
