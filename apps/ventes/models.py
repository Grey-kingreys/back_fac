"""
apps/ventes/models.py
Client, ParametresFidelite, Commande, LigneCommande, Paiement
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ParametresFidelite(models.Model):
    """Barème fidélité par entreprise (OneToOne)."""
    company = models.OneToOneField(
        'companies.Company', on_delete=models.CASCADE,
        related_name='parametres_fidelite', verbose_name=_("Entreprise"),
    )
    is_active = models.BooleanField(_("Activé"), default=False)
    tranche_montant = models.DecimalField(
        _("Tranche montant (GNF)"), max_digits=12, decimal_places=2, default=10000,
        help_text="Pour chaque tranche achetée, le client gagne des points",
    )
    points_par_tranche = models.PositiveIntegerField(
        _("Points par tranche"), default=1,
    )
    valeur_point_gnf = models.DecimalField(
        _("Valeur d'un point (GNF)"), max_digits=10, decimal_places=2, default=100,
        help_text="1 point = x GNF de réduction",
    )

    class Meta:
        verbose_name = _("Paramètres fidélité")
        verbose_name_plural = _("Paramètres fidélité")

    def __str__(self):
        return f"Fidélité — {self.company.name}"

    def calculer_points(self, montant_achat):
        if not self.is_active or self.tranche_montant <= 0:
            return 0
        return int(montant_achat / self.tranche_montant) * self.points_par_tranche


class Client(models.Model):
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='clients', verbose_name=_("Entreprise"),
    )
    code = models.CharField(_("Code"), max_length=30)
    nom = models.CharField(_("Nom"), max_length=150)
    prenom = models.CharField(_("Prénom"), max_length=100, blank=True)
    telephone = models.CharField(_("Téléphone"), max_length=30, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    adresse = models.TextField(_("Adresse"), blank=True)
    points_fidelite = models.PositiveIntegerField(_("Points fidélité"), default=0)
    solde_credit = models.DecimalField(
        _("Solde crédit (GNF)"), max_digits=14, decimal_places=2, default=0,
        help_text="Montant dû par le client (créances)",
    )
    is_active = models.BooleanField(_("Actif"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")
        ordering = ['company', 'nom']
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'],
                                    name='unique_client_code_per_company')
        ]

    def __str__(self):
        return f"{self.code} — {self.nom} {self.prenom}".strip()

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenom}".strip()


class Commande(models.Model):

    class Statut(models.TextChoices):
        BROUILLON = 'brouillon', _("Brouillon")
        CONFIRMEE = 'confirmee', _("Confirmée")
        EN_PREPARATION = 'en_preparation', _("En préparation")
        LIVREE = 'livree', _("Livrée")
        ANNULEE = 'annulee', _("Annulée")

    class ModePaiement(models.TextChoices):
        COMPTANT = 'comptant', _("Comptant")
        PARTIEL = 'partiel', _("Partiel")
        CREDIT = 'credit', _("Crédit")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='commandes', verbose_name=_("Entreprise"),
    )
    depot = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='commandes', verbose_name=_("Dépôt"),
    )
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='commandes', verbose_name=_("Client"),
    )
    numero = models.CharField(_("Numéro"), max_length=30, unique=True)
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.BROUILLON,
    )
    mode_paiement = models.CharField(
        _("Mode paiement"), max_length=20, choices=ModePaiement.choices,
        default=ModePaiement.COMPTANT,
    )
    montant_ht = models.DecimalField(
        _("Montant HT"), max_digits=14, decimal_places=2, default=0,
    )
    tva_total = models.DecimalField(
        _("Total TVA"), max_digits=14, decimal_places=2, default=0,
    )
    montant_ttc = models.DecimalField(
        _("Montant TTC"), max_digits=14, decimal_places=2, default=0,
    )
    remise = models.DecimalField(
        _("Remise (GNF)"), max_digits=12, decimal_places=2, default=0,
    )
    montant_paye = models.DecimalField(
        _("Montant payé"), max_digits=14, decimal_places=2, default=0,
    )
    points_utilises = models.PositiveIntegerField(_("Points fidélité utilisés"), default=0)
    points_gagnes = models.PositiveIntegerField(_("Points fidélité gagnés"), default=0)
    notes = models.TextField(_("Notes"), blank=True)
    caissier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='commandes_saisies', verbose_name=_("Caissier"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Commande")
        verbose_name_plural = _("Commandes")
        ordering = ['-created_at']

    def __str__(self):
        return self.numero

    def save(self, *args, **kwargs):
        if not self.numero:
            count = Commande.objects.filter(company=self.company).count() + 1
            self.numero = f"CMD-{timezone.now().strftime('%Y%m')}-{count:05d}"
        super().save(*args, **kwargs)

    @property
    def reste_a_payer(self):
        return max(self.montant_ttc - self.remise - self.montant_paye, 0)

    @property
    def est_solde(self):
        return self.reste_a_payer == 0


class LigneCommande(models.Model):
    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE,
        related_name='lignes', verbose_name=_("Commande"),
    )
    produit = models.ForeignKey(
        'produits.Produit', on_delete=models.PROTECT,
        related_name='lignes_commande', verbose_name=_("Produit"),
    )
    quantite = models.DecimalField(_("Quantité"), max_digits=12, decimal_places=3)
    prix_unitaire_ht = models.DecimalField(
        _("Prix unitaire HT"), max_digits=12, decimal_places=2,
    )
    tva_taux = models.DecimalField(
        _("Taux TVA (%)"), max_digits=5, decimal_places=2, default=0,
    )
    montant_ht = models.DecimalField(
        _("Montant HT"), max_digits=14, decimal_places=2,
    )
    montant_tva = models.DecimalField(
        _("Montant TVA"), max_digits=14, decimal_places=2, default=0,
    )
    montant_ttc = models.DecimalField(
        _("Montant TTC"), max_digits=14, decimal_places=2,
    )

    class Meta:
        verbose_name = _("Ligne de commande")
        verbose_name_plural = _("Lignes de commande")
        constraints = [
            models.UniqueConstraint(fields=['commande', 'produit'],
                                    name='unique_ligne_commande_produit')
        ]

    def __str__(self):
        return f"{self.produit.reference} x{self.quantite}"

    def save(self, *args, **kwargs):
        self.montant_ht = self.quantite * self.prix_unitaire_ht
        self.montant_tva = self.montant_ht * self.tva_taux / 100
        self.montant_ttc = self.montant_ht + self.montant_tva
        super().save(*args, **kwargs)


class Paiement(models.Model):

    class Mode(models.TextChoices):
        ESPECES = 'especes', _("Espèces")
        ORANGE_MONEY = 'orange_money', _("Orange Money")
        MTN_MONEY = 'mtn_money', _("MTN Money")
        VIREMENT = 'virement', _("Virement bancaire")
        POINTS_FIDELITE = 'points_fidelite', _("Points fidélité")

    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE,
        related_name='paiements', verbose_name=_("Commande"),
    )
    montant = models.DecimalField(_("Montant"), max_digits=14, decimal_places=2)
    mode = models.CharField(_("Mode"), max_length=20, choices=Mode.choices)
    reference = models.CharField(
        _("Référence"), max_length=100, blank=True,
        help_text="Numéro de transaction mobile money / virement",
    )
    caissier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='paiements_saisis', verbose_name=_("Caissier"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.commande.numero} — {self.get_mode_display()} : {self.montant} GNF"
