"""
apps/logistique/models.py
Flotte véhicules, missions de transport, positions GPS, signatures.
"""

import uuid

from django.conf import settings
from django.db import models, transaction
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
    annee = models.PositiveSmallIntegerField(
        _("Année de fabrication"), null=True, blank=True,
    )
    kilometrage_actuel = models.PositiveIntegerField(
        _("Kilométrage actuel (km)"), default=0,
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

    class TypeMission(models.TextChoices):
        TRANSFERT = 'transfert', _("Transfert inter-dépôt")
        LIVRAISON = 'livraison', _("Livraison client")
        ENLEVEMENT = 'enlevement', _("Enlèvement fournisseur")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='missions', verbose_name=_("Entreprise"),
    )
    numero = models.CharField(_("Numéro"), max_length=30)
    qr_code = models.UUIDField(
        _("QR Code"), default=uuid.uuid4, unique=True, editable=False,
    )
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
    type_mission = models.CharField(
        _("Type de mission"), max_length=20, choices=TypeMission.choices,
        default=TypeMission.TRANSFERT,
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
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'numero'],
                name='unique_mission_numero_per_company',
            )
        ]

    def __str__(self):
        return self.numero

    def save(self, *args, **kwargs):
        if not self.numero:
            with transaction.atomic():
                count = (
                    Mission.objects
                    .select_for_update()
                    .filter(company=self.company)
                    .count() + 1
                )
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


# ── Maintenance ───────────────────────────────────────────────────────────────
class Maintenance(models.Model):

    class TypeMaintenance(models.TextChoices):
        PREVENTIVE = 'preventive', _("Préventive")
        CORRECTIVE = 'corrective', _("Corrective")

    class Statut(models.TextChoices):
        PLANIFIEE = 'planifiee', _("Planifiée")
        EN_COURS = 'en_cours', _("En cours")
        TERMINEE = 'terminee', _("Terminée")

    vehicule = models.ForeignKey(
        Vehicule, on_delete=models.CASCADE,
        related_name='maintenances', verbose_name=_("Véhicule"),
    )
    type_maintenance = models.CharField(
        _("Type"), max_length=20, choices=TypeMaintenance.choices,
    )
    description = models.TextField(_("Description"))
    kilometrage_au_moment = models.PositiveIntegerField(
        _("Kilométrage au moment"), default=0,
    )
    cout = models.DecimalField(
        _("Coût (GNF)"), max_digits=14, decimal_places=2, default=0,
    )
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.PLANIFIEE,
    )
    date_planifiee = models.DateField(_("Date planifiée"))
    date_reelle = models.DateField(_("Date réelle"), null=True, blank=True)
    effectue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='maintenances_effectuees', verbose_name=_("Effectué par"),
    )
    notes = models.TextField(_("Notes"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Maintenance")
        verbose_name_plural = _("Maintenances")
        ordering = ['-date_planifiee']

    def __str__(self):
        return (f"{self.get_type_maintenance_display()} — "
                f"{self.vehicule.immatriculation} ({self.date_planifiee})")


# ── Pannes ────────────────────────────────────────────────────────────────────
class Panne(models.Model):

    class Statut(models.TextChoices):
        DECLAREE = 'declaree', _("Déclarée")
        EN_REPARATION = 'en_reparation', _("En réparation")
        RESOLUE = 'resolue', _("Résolue")

    vehicule = models.ForeignKey(
        Vehicule, on_delete=models.CASCADE,
        related_name='pannes', verbose_name=_("Véhicule"),
    )
    description = models.TextField(_("Description"))
    date_declaration = models.DateTimeField(_("Date de déclaration"), auto_now_add=True)
    mission = models.ForeignKey(
        Mission, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pannes', verbose_name=_("Mission en cours"),
    )
    cout_reparation = models.DecimalField(
        _("Coût réparation (GNF)"), max_digits=14, decimal_places=2,
        null=True, blank=True,
    )
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.DECLAREE,
    )
    declare_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='pannes_declarees', verbose_name=_("Déclaré par"),
    )
    resolu_le = models.DateTimeField(_("Résolu le"), null=True, blank=True)

    class Meta:
        verbose_name = _("Panne")
        verbose_name_plural = _("Pannes")
        ordering = ['-date_declaration']

    def __str__(self):
        return f"Panne {self.vehicule.immatriculation} — {self.get_statut_display()}"


# ── Documents véhicule ────────────────────────────────────────────────────────
class DocumentVehicule(models.Model):

    class TypeDocument(models.TextChoices):
        ASSURANCE = 'assurance', _("Assurance")
        VISITE_TECHNIQUE = 'visite_technique', _("Visite technique")
        CARTE_GRISE = 'carte_grise', _("Carte grise")
        AUTRE = 'autre', _("Autre")

    vehicule = models.ForeignKey(
        Vehicule, on_delete=models.CASCADE,
        related_name='documents', verbose_name=_("Véhicule"),
    )
    type_document = models.CharField(
        _("Type"), max_length=30, choices=TypeDocument.choices,
    )
    fichier = models.FileField(_("Fichier"), upload_to='vehicules/documents/')
    date_expiration = models.DateField(_("Date d'expiration"), null=True, blank=True)
    notes = models.CharField(_("Notes"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Document véhicule")
        verbose_name_plural = _("Documents véhicule")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_document_display()} — {self.vehicule.immatriculation}"

    @property
    def is_expire(self):
        if self.date_expiration is None:
            return False
        from django.utils import timezone
        return self.date_expiration < timezone.now().date()


# ── Consommation carburant ────────────────────────────────────────────────────
class ConsommationCarburant(models.Model):
    """Enregistrement de consommation carburant d'un véhicule."""

    class TypeCarburant(models.TextChoices):
        ESSENCE = 'essence', _("Essence")
        GASOIL = 'gasoil', _("Gasoil")
        GPL = 'gpl', _("GPL")

    vehicule = models.ForeignKey(
        Vehicule, on_delete=models.CASCADE,
        related_name='consommations_carburant', verbose_name=_("Véhicule"),
    )
    mission = models.ForeignKey(
        Mission, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='consommations_carburant',
        verbose_name=_("Mission"),
    )
    type_carburant = models.CharField(
        _("Type de carburant"), max_length=20, choices=TypeCarburant.choices,
        default=TypeCarburant.GASOIL,
    )
    quantite_litres = models.DecimalField(
        _("Quantité (litres)"), max_digits=8, decimal_places=2,
    )
    prix_par_litre = models.DecimalField(
        _("Prix par litre (GNF)"), max_digits=10, decimal_places=2,
    )
    kilometrage = models.PositiveIntegerField(_("Kilométrage au plein"))
    date_plein = models.DateField(_("Date du plein"))
    station = models.CharField(_("Station"), max_length=150, blank=True)
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='pleins_enregistres', verbose_name=_("Enregistré par"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Consommation carburant")
        verbose_name_plural = _("Consommations carburant")
        ordering = ['-date_plein']

    def __str__(self):
        return f"{self.vehicule.immatriculation} — {self.quantite_litres}L ({self.date_plein})"

    @property
    def montant_total(self):
        return self.quantite_litres * self.prix_par_litre
