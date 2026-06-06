"""
apps/produits/models.py
Modèles : Categorie, Unite, Fournisseur, Produit
"""

from django.db import models
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
