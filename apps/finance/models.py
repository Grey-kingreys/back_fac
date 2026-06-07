"""
apps/finance/models.py
Caisses physiques, sessions, transactions, Mobile Money, taux de change.
Hiérarchie : Entreprise → Zone → Dépôt → Session Caissier
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TauxChange(models.Model):
    """Taux de conversion entre devises (GNF ↔ USD, EUR, etc.)."""
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='taux_change', verbose_name=_("Entreprise"),
    )
    devise_source = models.CharField(_("Devise source"), max_length=10, default='USD')
    devise_cible = models.CharField(_("Devise cible"), max_length=10, default='GNF')
    taux = models.DecimalField(_("Taux"), max_digits=14, decimal_places=4)
    date_expiration = models.DateField(_("Date d'expiration"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='taux_saisis',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Taux de change")
        verbose_name_plural = _("Taux de change")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.devise_source}/{self.devise_cible} = {self.taux}"

    @property
    def est_expire(self):
        if not self.date_expiration:
            return False
        return timezone.now().date() > self.date_expiration


class CaissePhysique(models.Model):
    """
    Caisse physique liée à un dépôt.
    Une seule caisse par dépôt. Jamais supprimée, jamais réouverte.
    """
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='caisses', verbose_name=_("Entreprise"),
    )
    depot = models.OneToOneField(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='caisse', verbose_name=_("Dépôt"),
    )
    nom = models.CharField(_("Nom"), max_length=150)
    devise = models.CharField(_("Devise"), max_length=10, default='GNF')
    solde_actuel = models.DecimalField(
        _("Solde actuel (GNF)"), max_digits=16, decimal_places=2, default=0,
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Caisse physique")
        verbose_name_plural = _("Caisses physiques")

    def __str__(self):
        return f"{self.nom} — {self.depot}"


class SessionCaisse(models.Model):
    """
    Session d'ouverture/fermeture de caisse par un caissier.
    Une session ne peut jamais être réouverte.
    """

    class Statut(models.TextChoices):
        OUVERTE = 'ouverte', _("Ouverte")
        FERMEE = 'fermee', _("Fermée")

    caisse = models.ForeignKey(
        CaissePhysique, on_delete=models.PROTECT,
        related_name='sessions', verbose_name=_("Caisse"),
    )
    caissier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='sessions_caisse', verbose_name=_("Caissier"),
    )
    statut = models.CharField(
        _("Statut"), max_length=10, choices=Statut.choices, default=Statut.OUVERTE,
    )
    solde_ouverture = models.DecimalField(
        _("Solde ouverture (GNF)"), max_digits=16, decimal_places=2, default=0,
    )
    solde_fermeture_theorique = models.DecimalField(
        _("Solde théorique fermeture"), max_digits=16, decimal_places=2,
        null=True, blank=True,
    )
    solde_fermeture_reel = models.DecimalField(
        _("Solde réel fermeture"), max_digits=16, decimal_places=2,
        null=True, blank=True,
    )
    ecart = models.DecimalField(
        _("Écart"), max_digits=14, decimal_places=2, default=0,
    )
    motif_ecart = models.TextField(
        _("Motif écart"), blank=True,
        help_text="Obligatoire si écart != 0",
    )
    ouvert_le = models.DateTimeField(_("Ouvert le"), auto_now_add=True)
    ferme_le = models.DateTimeField(_("Fermé le"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Session caisse")
        verbose_name_plural = _("Sessions caisse")
        ordering = ['-ouvert_le']

    def __str__(self):
        return f"Session {self.caisse} — {self.caissier} ({self.statut})"

    def fermer(self, solde_reel, motif_ecart=''):
        from decimal import Decimal
        self.solde_fermeture_reel = Decimal(str(solde_reel))
        self.ecart = self.solde_fermeture_reel - (self.solde_fermeture_theorique or 0)
        if self.ecart != 0 and not motif_ecart:
            raise ValueError("Un motif est obligatoire si l'écart est non nul.")
        self.motif_ecart = motif_ecart
        self.statut = self.Statut.FERMEE
        self.ferme_le = timezone.now()
        self.save()


class TransactionCaisse(models.Model):
    """Mouvement de fonds dans une session de caisse."""

    class TypeTransaction(models.TextChoices):
        ENTREE = 'entree', _("Entrée")
        SORTIE = 'sortie', _("Sortie")
        VENTE = 'vente', _("Vente")
        REMBOURSEMENT = 'remboursement', _("Remboursement")
        APPROVISIONNEMENT = 'approvisionnement', _("Approvisionnement caisse")
        RETRAIT = 'retrait', _("Retrait")

    session = models.ForeignKey(
        SessionCaisse, on_delete=models.PROTECT,
        related_name='transactions', verbose_name=_("Session"),
    )
    type_transaction = models.CharField(
        _("Type"), max_length=20, choices=TypeTransaction.choices,
    )
    montant = models.DecimalField(_("Montant (GNF)"), max_digits=14, decimal_places=2)
    reference_doc = models.CharField(
        _("Référence document"), max_length=50, blank=True,
        help_text="Numéro de commande ou autre",
    )
    description = models.TextField(_("Description"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='transactions_caisse',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Transaction caisse")
        verbose_name_plural = _("Transactions caisse")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_transaction_display()} {self.montant} GNF — {self.session}"


class CompteMobileMoney(models.Model):
    """Compte Orange Money ou MTN Money lié à un dépôt."""

    class Operateur(models.TextChoices):
        ORANGE = 'orange_money', _("Orange Money")
        MTN = 'mtn_money', _("MTN Money")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='comptes_mobile_money', verbose_name=_("Entreprise"),
    )
    depot = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='comptes_mobile_money', verbose_name=_("Dépôt"),
    )
    operateur = models.CharField(
        _("Opérateur"), max_length=20, choices=Operateur.choices,
    )
    numero = models.CharField(_("Numéro"), max_length=20)
    nom_titulaire = models.CharField(_("Nom titulaire"), max_length=150)
    solde = models.DecimalField(
        _("Solde (GNF)"), max_digits=16, decimal_places=2, default=0,
    )
    is_active = models.BooleanField(_("Actif"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Compte Mobile Money")
        verbose_name_plural = _("Comptes Mobile Money")
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'operateur', 'numero'],
                name='unique_compte_mobile_money',
            )
        ]

    def __str__(self):
        return f"{self.get_operateur_display()} — {self.numero}"


class TransactionMobileMoney(models.Model):
    """Mouvement de fonds sur un compte Mobile Money."""

    class TypeTransaction(models.TextChoices):
        DEPOT = 'depot', _("Dépôt")
        RETRAIT = 'retrait', _("Retrait")
        PAIEMENT_RECU = 'paiement_recu', _("Paiement reçu")
        PAIEMENT_ENVOYE = 'paiement_envoye', _("Paiement envoyé")

    compte = models.ForeignKey(
        CompteMobileMoney, on_delete=models.PROTECT,
        related_name='transactions', verbose_name=_("Compte"),
    )
    type_transaction = models.CharField(
        _("Type"), max_length=20, choices=TypeTransaction.choices,
    )
    montant = models.DecimalField(_("Montant (GNF)"), max_digits=14, decimal_places=2)
    reference_operateur = models.CharField(
        _("Référence opérateur"), max_length=100, blank=True,
    )
    reference_doc = models.CharField(
        _("Référence document interne"), max_length=50, blank=True,
    )
    description = models.TextField(_("Description"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='transactions_mobile_money',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Transaction Mobile Money")
        verbose_name_plural = _("Transactions Mobile Money")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_transaction_display()} {self.montant} — {self.compte}"


# ── Hiérarchie caisses : Zone + Entreprise ────────────────────────────────────
class CaisseZone(models.Model):
    """Caisse consolidée au niveau zone (agrège les CaissePhysique de ses dépôts)."""
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='caisses_zone', verbose_name=_("Entreprise"),
    )
    zone = models.OneToOneField(
        'companies.Zone', on_delete=models.PROTECT,
        related_name='caisse', verbose_name=_("Zone"),
    )
    nom = models.CharField(_("Nom"), max_length=150)
    devise = models.CharField(_("Devise"), max_length=10, default='GNF')
    solde_actuel = models.DecimalField(
        _("Solde actuel (GNF)"), max_digits=16, decimal_places=2, default=0,
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Caisse zone")
        verbose_name_plural = _("Caisses zone")

    def __str__(self):
        return f"{self.nom} — {self.zone}"


class CaisseEntreprise(models.Model):
    """Caisse consolidée au niveau entreprise (agrège les CaisseZone)."""
    company = models.OneToOneField(
        'companies.Company', on_delete=models.PROTECT,
        related_name='caisse_entreprise', verbose_name=_("Entreprise"),
    )
    nom = models.CharField(_("Nom"), max_length=150)
    devise = models.CharField(_("Devise"), max_length=10, default='GNF')
    solde_actuel = models.DecimalField(
        _("Solde actuel (GNF)"), max_digits=16, decimal_places=2, default=0,
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Caisse entreprise")
        verbose_name_plural = _("Caisses entreprise")

    def __str__(self):
        return f"{self.nom} — {self.company}"


class VersementCaisse(models.Model):
    """Versement inter-niveaux : Dépôt→Zone ou Zone→Entreprise."""

    class TypeVersement(models.TextChoices):
        DEPOT_VERS_ZONE = 'depot_vers_zone', _("Dépôt → Zone")
        ZONE_VERS_ENTREPRISE = 'zone_vers_entreprise', _("Zone → Entreprise")

    type_versement = models.CharField(
        _("Type versement"), max_length=30, choices=TypeVersement.choices,
    )
    caisse_source_depot = models.ForeignKey(
        CaissePhysique, on_delete=models.PROTECT,
        null=True, blank=True, related_name='versements_source',
        verbose_name=_("Caisse source (dépôt)"),
    )
    caisse_source_zone = models.ForeignKey(
        CaisseZone, on_delete=models.PROTECT,
        null=True, blank=True, related_name='versements_source',
        verbose_name=_("Caisse source (zone)"),
    )
    caisse_dest_zone = models.ForeignKey(
        CaisseZone, on_delete=models.PROTECT,
        null=True, blank=True, related_name='versements_dest',
        verbose_name=_("Caisse destination (zone)"),
    )
    caisse_dest_entreprise = models.ForeignKey(
        CaisseEntreprise, on_delete=models.PROTECT,
        null=True, blank=True, related_name='versements_dest',
        verbose_name=_("Caisse destination (entreprise)"),
    )
    montant = models.DecimalField(_("Montant"), max_digits=16, decimal_places=2)
    justificatif = models.FileField(
        _("Justificatif"), upload_to='finance/versements/%Y/%m/',
        null=True, blank=True,
    )
    montant_comptage_receveur = models.DecimalField(
        _("Montant comptage receveur (double comptage)"),
        max_digits=16, decimal_places=2, null=True, blank=True,
    )
    motif_ecart = models.TextField(_("Motif écart"), blank=True)
    effectue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='versements_effectues', verbose_name=_("Effectué par"),
    )
    recu_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='versements_recus',
        verbose_name=_("Reçu par"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Versement caisse")
        verbose_name_plural = _("Versements caisse")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_versement_display()} — {self.montant} GNF"

    @property
    def ecart(self):
        if self.montant_comptage_receveur is None:
            return None
        return self.montant_comptage_receveur - self.montant


# ── Dépenses opérationnelles ──────────────────────────────────────────────────
class DepenseOperationnelle(models.Model):
    """Dépense opérationnelle par catégorie (carburant, maintenance, salaires…)."""

    class Categorie(models.TextChoices):
        CARBURANT = 'carburant', _("Carburant")
        MAINTENANCE = 'maintenance', _("Maintenance")
        SALAIRES = 'salaires', _("Salaires")
        LOYER = 'loyer', _("Loyer")
        FOURNITURES = 'fournitures', _("Fournitures")
        TRANSPORT = 'transport', _("Transport")
        AUTRE = 'autre', _("Autre")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='depenses_operationnelles', verbose_name=_("Entreprise"),
    )
    depot = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        null=True, blank=True, related_name='depenses_operationnelles',
        verbose_name=_("Dépôt"),
    )
    categorie = models.CharField(
        _("Catégorie"), max_length=20, choices=Categorie.choices,
    )
    montant = models.DecimalField(_("Montant (GNF)"), max_digits=14, decimal_places=2)
    description = models.TextField(_("Description"))
    date_depense = models.DateField(_("Date de la dépense"))
    reference = models.CharField(_("Référence"), max_length=100, blank=True)
    justificatif = models.FileField(
        _("Justificatif"), upload_to='finance/depenses/%Y/%m/',
        null=True, blank=True,
    )
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='depenses_enregistrees', verbose_name=_("Enregistré par"),
    )
    session_caisse = models.ForeignKey(
        SessionCaisse, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='depenses',
        verbose_name=_("Session caisse liée"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Dépense opérationnelle")
        verbose_name_plural = _("Dépenses opérationnelles")
        ordering = ['-date_depense']

    def __str__(self):
        return f"{self.get_categorie_display()} — {self.montant} GNF ({self.date_depense})"
