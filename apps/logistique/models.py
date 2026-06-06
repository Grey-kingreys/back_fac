"""
apps/logistique/models.py
Flotte véhicules, missions de transport, positions GPS, signatures.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Vehicule(models.Model):

    class Statut(models.TextChoices):
        DISPONIBLE = 'disponible', _("Disponible")
        EN_MISSION = 'en_mission', _("En mission")
        MAINTENANCE = 'maintenance', _("En maintenance")
        HORS_SERVICE = 'hors_service', _("Hors service")

    class TypeVehicule(models.TextChoices):
        CAMION = 'camion', _("Camion")
        CAMIONNETTE = 'camionnette', _("Camionnette")
        MOTO = 'moto', _("Moto")
        VOITURE = 'voiture', _("Voiture")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='vehicules', verbose_name=_("Entreprise"),
    )
    immatriculation = models.CharField(_("Immatriculation"), max_length=30)
    type_vehicule = models.CharField(
        _("Type"), max_length=20, choices=TypeVehicule.choices,
    )
    marque = models.CharField(_("Marque"), max_length=100, blank=True)
    modele = models.CharField(_("Modèle"), max_length=100, blank=True)
    capacite_kg = models.DecimalField(
        _("Capacité (kg)"), max_digits=10, decimal_places=2, null=True, blank=True,
    )
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.DISPONIBLE,
    )
    chauffeur_attitré = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vehicules_assignes', verbose_name=_("Chauffeur attitré"),
    )
    has_nfc = models.BooleanField(_("Puce NFC"), default=False)
    nfc_tag = models.CharField(_("Tag NFC"), max_length=100, blank=True)
    is_active = models.BooleanField(_("Actif"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Véhicule")
        verbose_name_plural = _("Véhicules")
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'immatriculation'],
                name='unique_immatriculation_par_company',
            )
        ]

    def __str__(self):
        return f"{self.immatriculation} — {self.get_type_vehicule_display()}"


class Mission(models.Model):

    class Statut(models.TextChoices):
        PLANIFIEE = 'planifiee', _("Planifiée")
        CHARGEMENT = 'chargement', _("En chargement")
        EN_TRANSIT = 'en_transit', _("En transit")
        ARRIVEE = 'arrivee', _("Arrivée à destination")
        LITIGE = 'litige', _("Litige")
        TERMINEE = 'terminee', _("Terminée")
        ANNULEE = 'annulee', _("Annulée")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='missions', verbose_name=_("Entreprise"),
    )
    numero = models.CharField(_("Numéro"), max_length=30, unique=True)
    vehicule = models.ForeignKey(
        Vehicule, on_delete=models.PROTECT,
        related_name='missions', verbose_name=_("Véhicule"),
    )
    chauffeur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='missions_conduites', verbose_name=_("Chauffeur"),
    )
    depot_depart = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='missions_depart', verbose_name=_("Dépôt départ"),
    )
    depot_arrivee = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='missions_arrivee', verbose_name=_("Dépôt arrivée"),
    )
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.PLANIFIEE,
    )
    transfert_stock = models.OneToOneField(
        'stocks.TransfertStock', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='mission', verbose_name=_("Transfert de stock associé"),
    )
    date_depart_prevue = models.DateTimeField(_("Départ prévu"), null=True, blank=True)
    date_depart_reelle = models.DateTimeField(_("Départ réel"), null=True, blank=True)
    date_arrivee_reelle = models.DateTimeField(_("Arrivée réelle"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    signature_arrivee = models.TextField(
        _("Signature arrivée (base64)"), blank=True,
        help_text="Canvas HTML5 encodé en base64",
    )
    motif_litige = models.TextField(_("Motif litige"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='missions_creees',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Mission")
        verbose_name_plural = _("Missions")
        ordering = ['-created_at']

    def __str__(self):
        return self.numero

    def save(self, *args, **kwargs):
        if not self.numero:
            count = Mission.objects.filter(company=self.company).count() + 1
            self.numero = f"MSN-{timezone.now().strftime('%Y%m')}-{count:04d}"
        super().save(*args, **kwargs)


class LigneMission(models.Model):
    """Détail des marchandises transportées dans une mission."""
    mission = models.ForeignKey(
        Mission, on_delete=models.CASCADE,
        related_name='lignes', verbose_name=_("Mission"),
    )
    produit = models.ForeignKey(
        'produits.Produit', on_delete=models.PROTECT,
        related_name='lignes_mission',
    )
    quantite = models.DecimalField(_("Quantité"), max_digits=12, decimal_places=3)
    quantite_recue = models.DecimalField(
        _("Quantité reçue"), max_digits=12, decimal_places=3, null=True, blank=True,
    )
    observations = models.TextField(_("Observations"), blank=True)

    class Meta:
        verbose_name = _("Ligne de mission")
        verbose_name_plural = _("Lignes de mission")

    def __str__(self):
        return f"{self.produit} x{self.quantite}"


class PositionGPS(models.Model):
    """Trace GPS du véhicule pendant une mission (polling 1 min)."""
    mission = models.ForeignKey(
        Mission, on_delete=models.CASCADE,
        related_name='positions', verbose_name=_("Mission"),
    )
    latitude = models.DecimalField(_("Latitude"), max_digits=10, decimal_places=7)
    longitude = models.DecimalField(_("Longitude"), max_digits=10, decimal_places=7)
    vitesse_kmh = models.DecimalField(
        _("Vitesse (km/h)"), max_digits=6, decimal_places=2, null=True, blank=True,
    )
    enregistre_le = models.DateTimeField(_("Enregistré le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Position GPS")
        verbose_name_plural = _("Positions GPS")
        ordering = ['-enregistre_le']

    def __str__(self):
        return f"GPS {self.mission.numero} — {self.latitude},{self.longitude}"
