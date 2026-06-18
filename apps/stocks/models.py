"""
apps/stocks/models.py
StockDepot, LotStock, MouvementStock, TransfertStock, LigneTransfert
"""

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone as tz
from django.utils.translation import gettext_lazy as _


class StockDepot(models.Model):
    """Niveau de stock agrégé d'un produit dans un dépôt donné."""
    depot = models.ForeignKey(
        'companies.Depot', on_delete=models.CASCADE,
        related_name='stocks', verbose_name=_("Dépôt"),
    )
    produit = models.ForeignKey(
        'produits.Produit', on_delete=models.CASCADE,
        related_name='stocks', verbose_name=_("Produit"),
    )
    quantite = models.DecimalField(
        _("Quantité"), max_digits=12, decimal_places=3, default=0,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Stock dépôt")
        verbose_name_plural = _("Stocks dépôts")
        constraints = [
            models.UniqueConstraint(fields=['depot', 'produit'],
                                    name='unique_stock_depot_produit')
        ]

    def __str__(self):
        return f"{self.produit.reference} @ {self.depot.code} : {self.quantite}"

    @property
    def company(self):
        return self.depot.zone.company

    @property
    def en_alerte(self):
        return self.quantite <= self.produit.seuil_alerte


class LotStock(models.Model):
    """Lot de stock avec numéro et date d'expiration (pour gestion FEFO)."""
    stock_depot = models.ForeignKey(
        StockDepot, on_delete=models.CASCADE,
        related_name='lots', verbose_name=_("Stock dépôt"),
    )
    numero_lot = models.CharField(_("Numéro de lot"), max_length=100, blank=True)
    quantite = models.DecimalField(
        _("Quantité"), max_digits=12, decimal_places=3, default=0,
    )
    date_fabrication = models.DateField(_("Date de fabrication"), null=True, blank=True)
    date_expiration = models.DateField(_("Date d'expiration"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Lot de stock")
        verbose_name_plural = _("Lots de stock")
        ordering = ['date_expiration', 'created_at']

    def __str__(self):
        return f"Lot {self.numero_lot} — exp. {self.date_expiration}"


class MouvementStock(models.Model):
    """Journal de tous les mouvements de stock."""

    class TypeMouvement(models.TextChoices):
        ENTREE = 'entree', _("Entrée")
        SORTIE = 'sortie', _("Sortie")
        TRANSFERT_DEPART = 'transfert_depart', _("Transfert — départ")
        TRANSFERT_ARRIVEE = 'transfert_arrivee', _("Transfert — arrivée")
        INVENTAIRE = 'inventaire', _("Inventaire")
        AJUSTEMENT = 'ajustement', _("Ajustement")

    depot = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='mouvements_stock', verbose_name=_("Dépôt"),
    )
    produit = models.ForeignKey(
        'produits.Produit', on_delete=models.PROTECT,
        related_name='mouvements', verbose_name=_("Produit"),
    )
    type_mouvement = models.CharField(
        _("Type"), max_length=30, choices=TypeMouvement.choices,
    )
    quantite = models.DecimalField(
        _("Quantité"), max_digits=12, decimal_places=3,
    )
    quantite_avant = models.DecimalField(
        _("Quantité avant"), max_digits=12, decimal_places=3,
    )
    quantite_apres = models.DecimalField(
        _("Quantité après"), max_digits=12, decimal_places=3,
    )
    reference_doc = models.CharField(
        _("Référence document"), max_length=100, blank=True,
        help_text="N° de commande, BL, transfert, etc.",
    )
    motif = models.TextField(_("Motif"), blank=True)
    transfert = models.ForeignKey(
        'stocks.TransfertStock', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='mouvements',
        verbose_name=_("Transfert lié"),
    )
    fournisseur = models.ForeignKey(
        'produits.Fournisseur', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='mouvements_stock',
        verbose_name=_("Fournisseur"),
        help_text="Renseigné lors des entrées liées à une livraison fournisseur",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='mouvements_stock', verbose_name=_("Utilisateur"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Mouvement de stock")
        verbose_name_plural = _("Mouvements de stock")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_mouvement_display()} — {self.produit.reference} ({self.quantite})"

    @property
    def company(self):
        return self.depot.zone.company


class TransfertStock(models.Model):
    """Transfert de stock entre deux dépôts."""

    class Statut(models.TextChoices):
        BROUILLON = 'brouillon', _("Brouillon")
        VALIDE = 'valide', _("Validé — en attente d'expédition")
        EN_TRANSIT = 'en_transit', _("En transit")
        RECU = 'recu', _("Reçu")
        ANNULE = 'annule', _("Annulé")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='transferts_stock', verbose_name=_("Entreprise"),
    )
    numero = models.CharField(_("Numéro"), max_length=30)
    depot_source = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='transferts_depart', verbose_name=_("Dépôt source"),
    )
    depot_destination = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='transferts_arrivee', verbose_name=_("Dépôt destination"),
    )
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.BROUILLON,
    )
    date_envoi = models.DateTimeField(_("Date d'envoi"), null=True, blank=True)
    date_reception = models.DateTimeField(_("Date de réception"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    utilisateur_envoi = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='transferts_envoyes', verbose_name=_("Envoyé par"),
    )
    utilisateur_reception = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transferts_recus', verbose_name=_("Reçu par"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Transfert de stock")
        verbose_name_plural = _("Transferts de stock")
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'numero'],
                name='unique_transfert_stock_numero_per_company',
            )
        ]

    def __str__(self):
        return f"TRF-{self.numero} ({self.get_statut_display()})"

    def save(self, *args, **kwargs):
        if not self.numero:
            with transaction.atomic():
                count = (
                    TransfertStock.objects
                    .select_for_update()
                    .filter(company=self.company)
                    .count() + 1
                )
                self.numero = f"TRF-{tz.now().strftime('%Y%m')}-{count:04d}"
        super().save(*args, **kwargs)


class LigneTransfert(models.Model):
    """Ligne produit d'un transfert de stock."""
    transfert = models.ForeignKey(
        TransfertStock, on_delete=models.CASCADE,
        related_name='lignes', verbose_name=_("Transfert"),
    )
    produit = models.ForeignKey(
        'produits.Produit', on_delete=models.PROTECT,
        related_name='lignes_transfert', verbose_name=_("Produit"),
    )
    quantite_envoyee = models.DecimalField(
        _("Qté envoyée"), max_digits=12, decimal_places=3,
    )
    quantite_recue = models.DecimalField(
        _("Qté reçue"), max_digits=12, decimal_places=3,
        null=True, blank=True,
    )
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Ligne de transfert")
        verbose_name_plural = _("Lignes de transfert")
        constraints = [
            models.UniqueConstraint(fields=['transfert', 'produit'],
                                    name='unique_ligne_transfert_produit')
        ]

    def __str__(self):
        return f"{self.produit.reference} x{self.quantite_envoyee}"


# ── Inventaires physiques ─────────────────────────────────────────────────────
class Inventaire(models.Model):
    """Inventaire physique d'un dépôt — comptage réel vs théorique."""

    class Statut(models.TextChoices):
        EN_COURS = 'en_cours', _("En cours")
        VALIDE = 'valide', _("Validé")
        ANNULE = 'annule', _("Annulé")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='inventaires', verbose_name=_("Entreprise"),
    )
    depot = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='inventaires', verbose_name=_("Dépôt"),
    )
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.EN_COURS,
    )
    numero = models.CharField(_("Numéro"), max_length=30)
    notes = models.TextField(_("Notes"), blank=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='inventaires_crees', verbose_name=_("Créé par"),
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='inventaires_valides', verbose_name=_("Validé par"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    valide_le = models.DateTimeField(_("Validé le"), null=True, blank=True)

    class Meta:
        verbose_name = _("Inventaire")
        verbose_name_plural = _("Inventaires")
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'numero'],
                name='unique_inventaire_numero_per_company',
            )
        ]

    def __str__(self):
        return f"{self.numero} — {self.depot} ({self.get_statut_display()})"

    def save(self, *args, **kwargs):
        if not self.numero:
            with transaction.atomic():
                count = (
                    Inventaire.objects
                    .select_for_update()
                    .filter(company=self.company)
                    .count() + 1
                )
                self.numero = f"INV-{tz.now().strftime('%Y%m')}-{count:04d}"
        super().save(*args, **kwargs)


class LigneInventaire(models.Model):
    """Ligne d'un inventaire : quantité théorique vs comptée."""
    inventaire = models.ForeignKey(
        Inventaire, on_delete=models.CASCADE,
        related_name='lignes', verbose_name=_("Inventaire"),
    )
    produit = models.ForeignKey(
        'produits.Produit', on_delete=models.PROTECT,
        related_name='lignes_inventaire', verbose_name=_("Produit"),
    )
    quantite_theorique = models.DecimalField(
        _("Quantité théorique"), max_digits=12, decimal_places=3,
        help_text="Lue depuis StockDepot au moment de la création de l'inventaire",
    )
    quantite_comptee = models.DecimalField(
        _("Quantité comptée"), max_digits=12, decimal_places=3,
        null=True, blank=True,
    )

    class Meta:
        verbose_name = _("Ligne d'inventaire")
        verbose_name_plural = _("Lignes d'inventaire")
        constraints = [
            models.UniqueConstraint(
                fields=['inventaire', 'produit'],
                name='unique_ligne_inventaire_produit',
            )
        ]

    def __str__(self):
        return f"{self.produit.reference} — {self.inventaire.numero}"

    @property
    def ecart(self):
        if self.quantite_comptee is None:
            return None
        return self.quantite_comptee - self.quantite_theorique


# ── Ajustements de stock ──────────────────────────────────────────────────────
class AjustementStock(models.Model):
    """Demande d'ajustement manuel de stock avec validation superviseur."""

    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', _("En attente")
        APPROUVE = 'approuve', _("Approuvé")
        REFUSE = 'refuse', _("Refusé")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='ajustements_stock', verbose_name=_("Entreprise"),
    )
    depot = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='ajustements_stock', verbose_name=_("Dépôt"),
    )
    produit = models.ForeignKey(
        'produits.Produit', on_delete=models.PROTECT,
        related_name='ajustements_stock', verbose_name=_("Produit"),
    )
    quantite = models.DecimalField(
        _("Quantité"), max_digits=12, decimal_places=3,
        help_text="Positif = ajout de stock, négatif = retrait",
    )
    motif = models.TextField(_("Motif"))
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE,
    )
    demande_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='ajustements_demandes', verbose_name=_("Demandé par"),
    )
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ajustements_traites', verbose_name=_("Traité par"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    traite_le = models.DateTimeField(_("Traité le"), null=True, blank=True)

    class Meta:
        verbose_name = _("Ajustement de stock")
        verbose_name_plural = _("Ajustements de stock")
        ordering = ['-created_at']

    def __str__(self):
        return f"Ajust. {self.produit.reference} @{self.depot.code} : {self.quantite:+}"
