"""
apps/produits/models.py
Modèles : Categorie, Unite, Fournisseur, Produit, CommandeFournisseur
"""

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Categorie(models.Model):
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='categories', verbose_name=_("Entreprise"),
    )
    name = models.CharField(_("Nom"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    couleur = models.CharField(_("Couleur"), max_length=7, default='#6366f1',
                               help_text="Code hexadécimal ex: #6366f1")
    tva_taux = models.DecimalField(
        _("Taux TVA par défaut (%)"), max_digits=5, decimal_places=2, default=0,
        help_text="Taux TVA appliqué par défaut aux produits de cette catégorie",
    )
    is_active = models.BooleanField(_("Actif"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Catégorie")
        verbose_name_plural = _("Catégories")
        ordering = ['company', 'name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'],
                                    name='unique_categorie_name_per_company')
        ]

    def __str__(self):
        return self.name


class Unite(models.Model):
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='unites', verbose_name=_("Entreprise"),
    )
    name = models.CharField(
        _("Nom"), max_length=100, help_text="Ex: Kilogramme, Litre, Carton")
    symbole = models.CharField(
        _("Symbole"), max_length=20, help_text="Ex: kg, L, ctn")
    is_active = models.BooleanField(_("Actif"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Unité de mesure")
        verbose_name_plural = _("Unités de mesure")
        ordering = ['company', 'name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'symbole'],
                                    name='unique_unite_symbole_per_company')
        ]

    def __str__(self):
        return f"{self.name} ({self.symbole})"


class Fournisseur(models.Model):
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='fournisseurs', verbose_name=_("Entreprise"),
    )
    code = models.CharField(_("Code"), max_length=30)
    nom = models.CharField(_("Nom"), max_length=255)
    telephone = models.CharField(_("Téléphone"), max_length=30, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    adresse = models.TextField(_("Adresse"), blank=True)
    solde_dette = models.DecimalField(
        _("Solde dette (GNF)"), max_digits=14, decimal_places=2, default=0,
        help_text="Montant total dû au fournisseur en GNF"
    )
    notes = models.TextField(_("Notes"), blank=True)
    is_active = models.BooleanField(_("Actif"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Fournisseur")
        verbose_name_plural = _("Fournisseurs")
        ordering = ['company', 'nom']
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'],
                                    name='unique_fournisseur_code_per_company')
        ]

    def __str__(self):
        return f"{self.code} — {self.nom}"


class Produit(models.Model):
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='produits', verbose_name=_("Entreprise"),
    )
    categorie = models.ForeignKey(
        Categorie, on_delete=models.PROTECT,
        related_name='produits', verbose_name=_("Catégorie"),
    )
    unite = models.ForeignKey(
        Unite, on_delete=models.PROTECT,
        related_name='produits', verbose_name=_("Unité"),
    )
    fournisseur_principal = models.ForeignKey(
        Fournisseur, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='produits_fournis', verbose_name=_("Fournisseur principal"),
    )
    reference = models.CharField(_("Référence"), max_length=60)
    code_barre = models.CharField(
        _("Code-barres"), max_length=64, blank=True, default='',
        help_text="Code-barres physique (EAN/UPC) scanné pour retrouver le produit",
    )
    nom = models.CharField(_("Nom"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    image = models.ImageField(
        upload_to='produits/images/', null=True, blank=True,
        verbose_name=_("Image"),
    )
    prix_achat = models.DecimalField(
        _("Prix d'achat (GNF)"), max_digits=14, decimal_places=2, default=0,
    )
    prix_vente = models.DecimalField(
        _("Prix de vente (GNF)"), max_digits=14, decimal_places=2, default=0,
    )
    seuil_alerte = models.DecimalField(
        _("Seuil d'alerte"), max_digits=10, decimal_places=2, default=0,
        help_text="Déclenchement d'une alerte si stock < seuil"
    )
    seuil_max = models.DecimalField(
        _("Stock maximum recommandé"), max_digits=10, decimal_places=2, default=0,
    )
    est_perimable = models.BooleanField(
        _("Périssable / FEFO"), default=False,
        help_text="Si True, la gestion FEFO s'applique (First Expired First Out)"
    )
    tva_taux = models.DecimalField(
        _("Taux TVA (%)"), max_digits=5, decimal_places=2, default=0,
    )
    is_active = models.BooleanField(_("Actif"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Produit")
        verbose_name_plural = _("Produits")
        ordering = ['company', 'nom']
        constraints = [
            models.UniqueConstraint(fields=['company', 'reference'],
                                    name='unique_produit_reference_per_company')
        ]

    def __str__(self):
        return f"{self.reference} — {self.nom}"

    @property
    def marge(self):
        if self.prix_achat > 0:
            return round((self.prix_vente - self.prix_achat) / self.prix_achat * 100, 2)
        return 0


# ── Commandes fournisseurs ────────────────────────────────────────────────────
class CommandeFournisseur(models.Model):
    """Commande passée à un fournisseur."""

    class Statut(models.TextChoices):
        BROUILLON = 'brouillon', _("Brouillon")
        ENVOYEE = 'envoyee', _("Envoyée")
        PARTIELLEMENT_RECUE = 'partiellement_recue', _("Partiellement reçue")
        RECUE = 'recue', _("Reçue")
        ANNULEE = 'annulee', _("Annulée")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='commandes_fournisseurs', verbose_name=_("Entreprise"),
    )
    fournisseur = models.ForeignKey(
        Fournisseur, on_delete=models.PROTECT,
        related_name='commandes', verbose_name=_("Fournisseur"),
    )
    numero = models.CharField(_("Numéro"), max_length=30)
    statut = models.CharField(
        _("Statut"), max_length=30, choices=Statut.choices, default=Statut.BROUILLON,
    )
    depot_destination = models.ForeignKey(
        'companies.Depot', on_delete=models.PROTECT,
        related_name='commandes_fournisseurs',
        verbose_name=_("Dépôt de réception"),
    )
    date_livraison_prevue = models.DateField(_("Date livraison prévue"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    created_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='commandes_fournisseur_creees', verbose_name=_("Créé par"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Commande fournisseur")
        verbose_name_plural = _("Commandes fournisseurs")
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'numero'],
                name='unique_commande_fournisseur_numero_per_company',
            )
        ]

    def __str__(self):
        return self.numero

    def save(self, *args, **kwargs):
        if not self.numero:
            with transaction.atomic():
                count = (
                    CommandeFournisseur.objects
                    .select_for_update()
                    .filter(company=self.company)
                    .count() + 1
                )
                self.numero = f"CDF-{timezone.now().strftime('%Y%m')}-{count:04d}"
        super().save(*args, **kwargs)


class LigneCommandeFournisseur(models.Model):
    """Ligne produit d'une commande fournisseur."""
    commande = models.ForeignKey(
        CommandeFournisseur, on_delete=models.CASCADE,
        related_name='lignes', verbose_name=_("Commande"),
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.PROTECT,
        related_name='lignes_commande_fournisseur', verbose_name=_("Produit"),
    )
    quantite_commandee = models.DecimalField(
        _("Quantité commandée"), max_digits=12, decimal_places=3,
    )
    prix_unitaire = models.DecimalField(
        _("Prix unitaire (GNF)"), max_digits=14, decimal_places=2,
    )
    quantite_recue = models.DecimalField(
        _("Quantité reçue"), max_digits=12, decimal_places=3, default=0,
    )

    class Meta:
        verbose_name = _("Ligne commande fournisseur")
        verbose_name_plural = _("Lignes commande fournisseur")
        constraints = [
            models.UniqueConstraint(
                fields=['commande', 'produit'],
                name='unique_ligne_commande_fournisseur_produit',
            )
        ]

    def __str__(self):
        return f"{self.produit.reference} x{self.quantite_commandee}"

    @property
    def montant_total(self):
        return self.quantite_commandee * self.prix_unitaire


class MouvementDetteFournisseur(models.Model):
    """Journal des mouvements de dette envers un fournisseur."""

    class TypeMouvement(models.TextChoices):
        DETTE_AJOUTEE = 'dette_ajoutee', _("Dette ajoutée")
        PAIEMENT_EFFECTUE = 'paiement_effectue', _("Paiement effectué")
        AVANCE = 'avance', _("Avance")

    fournisseur = models.ForeignKey(
        Fournisseur, on_delete=models.CASCADE,
        related_name='mouvements_dette', verbose_name=_("Fournisseur"),
    )
    type_mouvement = models.CharField(
        _("Type"), max_length=20, choices=TypeMouvement.choices,
    )
    montant = models.DecimalField(_("Montant (GNF)"), max_digits=14, decimal_places=2)
    reference = models.CharField(_("Référence"), max_length=100, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    created_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='mouvements_dette_crees', verbose_name=_("Créé par"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Mouvement dette fournisseur")
        verbose_name_plural = _("Mouvements dette fournisseur")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_mouvement_display()} — {self.fournisseur} : {self.montant} GNF"


class EvaluationFournisseur(models.Model):
    """Évaluation d'un fournisseur après réception d'une commande."""

    class Note(models.IntegerChoices):
        TRES_MAUVAIS = 1, _("1 — Très mauvais")
        MAUVAIS = 2, _("2 — Mauvais")
        MOYEN = 3, _("3 — Moyen")
        BON = 4, _("4 — Bon")
        EXCELLENT = 5, _("5 — Excellent")

    fournisseur = models.ForeignKey(
        Fournisseur, on_delete=models.CASCADE,
        related_name='evaluations', verbose_name=_("Fournisseur"),
    )
    commande = models.OneToOneField(
        'CommandeFournisseur', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='evaluation',
        verbose_name=_("Commande liée"),
    )
    note_qualite = models.PositiveSmallIntegerField(
        _("Note qualité produits"), choices=Note.choices,
    )
    note_delai = models.PositiveSmallIntegerField(
        _("Note respect des délais"), choices=Note.choices,
    )
    note_service = models.PositiveSmallIntegerField(
        _("Note service client"), choices=Note.choices,
    )
    commentaire = models.TextField(_("Commentaire"), blank=True)
    evalue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='evaluations_fournisseur', verbose_name=_("Évalué par"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Évaluation fournisseur")
        verbose_name_plural = _("Évaluations fournisseurs")
        ordering = ['-created_at']

    def __str__(self):
        return f"Éval. {self.fournisseur} — {self.note_globale:.1f}/5"

    @property
    def note_globale(self):
        return (self.note_qualite + self.note_delai + self.note_service) / 3
