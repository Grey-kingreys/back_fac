"""
apps/rh/models.py
Employés, présences, congés, documents, objectifs commerciaux.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Employe(models.Model):

    class Statut(models.TextChoices):
        ACTIF = 'actif', _("Actif")
        CONGE = 'conge', _("En congé")
        SUSPENDU = 'suspendu', _("Suspendu")
        QUITTE = 'quitte', _("A quitté")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='employes', verbose_name=_("Entreprise"),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='profil_employe', verbose_name=_("Compte utilisateur"),
    )
    depot = models.ForeignKey(
        'companies.Depot', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='employes',
    )
    matricule = models.CharField(_("Matricule"), max_length=30)
    nom = models.CharField(_("Nom"), max_length=150)
    prenom = models.CharField(_("Prénom"), max_length=100, blank=True)
    telephone = models.CharField(_("Téléphone"), max_length=30, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    poste = models.CharField(_("Poste"), max_length=150, blank=True)
    date_embauche = models.DateField(_("Date d'embauche"), null=True, blank=True)
    salaire_base = models.DecimalField(
        _("Salaire de base (GNF)"), max_digits=14, decimal_places=2, default=0,
    )
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.ACTIF,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Employé")
        verbose_name_plural = _("Employés")
        ordering = ['company', 'nom']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'matricule'],
                name='unique_matricule_par_company',
            )
        ]

    def __str__(self):
        return f"{self.matricule} — {self.nom} {self.prenom}".strip()

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenom}".strip()


class Presence(models.Model):

    class TypePresence(models.TextChoices):
        PRESENT = 'present', _("Présent")
        ABSENT = 'absent', _("Absent")
        RETARD = 'retard', _("Retard")
        MISSION = 'mission', _("En mission")

    employe = models.ForeignKey(
        Employe, on_delete=models.CASCADE,
        related_name='presences', verbose_name=_("Employé"),
    )
    date = models.DateField(_("Date"))
    type_presence = models.CharField(
        _("Type"), max_length=20, choices=TypePresence.choices,
    )
    heure_arrivee = models.TimeField(_("Heure d'arrivée"), null=True, blank=True)
    heure_depart = models.TimeField(_("Heure de départ"), null=True, blank=True)
    observations = models.TextField(_("Observations"), blank=True)
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='presences_enregistrees',
    )

    class Meta:
        verbose_name = _("Présence")
        verbose_name_plural = _("Présences")
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['employe', 'date'],
                name='unique_presence_employe_date',
            )
        ]

    def __str__(self):
        return f"{self.employe} — {self.date} ({self.get_type_presence_display()})"


class Conge(models.Model):

    class TypeConge(models.TextChoices):
        ANNUEL = 'annuel', _("Congé annuel")
        MALADIE = 'maladie', _("Congé maladie")
        MATERNITE = 'maternite', _("Congé maternité")
        SANS_SOLDE = 'sans_solde', _("Sans solde")
        AUTRE = 'autre', _("Autre")

    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', _("En attente")
        APPROUVE = 'approuve', _("Approuvé")
        REFUSE = 'refuse', _("Refusé")
        ANNULE = 'annule', _("Annulé")

    employe = models.ForeignKey(
        Employe, on_delete=models.CASCADE,
        related_name='conges', verbose_name=_("Employé"),
    )
    type_conge = models.CharField(
        _("Type"), max_length=20, choices=TypeConge.choices,
    )
    date_debut = models.DateField(_("Date début"))
    date_fin = models.DateField(_("Date fin"))
    statut = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE,
    )
    motif = models.TextField(_("Motif"), blank=True)
    approuve_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='conges_approuves',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Congé")
        verbose_name_plural = _("Congés")
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.employe} — {self.get_type_conge_display()} ({self.date_debut}/{self.date_fin})"

    @property
    def nb_jours(self):
        return (self.date_fin - self.date_debut).days + 1


class Document(models.Model):

    class TypeDocument(models.TextChoices):
        CONTRAT = 'contrat', _("Contrat de travail")
        FACTURE_FOURNISSEUR = 'facture_fournisseur', _("Facture fournisseur")
        BON_LIVRAISON = 'bon_livraison', _("Bon de livraison")
        AUTRE = 'autre', _("Autre")

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='documents', verbose_name=_("Entreprise"),
    )
    type_document = models.CharField(
        _("Type"), max_length=30, choices=TypeDocument.choices,
    )
    titre = models.CharField(_("Titre"), max_length=255)
    fichier = models.FileField(_("Fichier"), upload_to='documents/%Y/%m/')
    employe = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documents',
    )
    commande = models.ForeignKey(
        'ventes.Commande', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents',
        verbose_name=_("Commande liée"),
    )
    mission = models.ForeignKey(
        'logistique.Mission', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents',
        verbose_name=_("Mission liée"),
    )
    transfert = models.ForeignKey(
        'stocks.TransfertStock', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents',
        verbose_name=_("Transfert lié"),
    )
    reference_externe = models.CharField(
        _("Référence externe"), max_length=100, blank=True,
    )
    notes = models.TextField(_("Notes"), blank=True)
    uploade_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='documents_uploades',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_document_display()} — {self.titre}"


class ObjectifVente(models.Model):
    """Objectif de vente mensuel par dépôt."""
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='objectifs_vente', verbose_name=_("Entreprise"),
    )
    depot = models.ForeignKey(
        'companies.Depot', on_delete=models.CASCADE,
        related_name='objectifs_vente', verbose_name=_("Dépôt"),
    )
    annee = models.PositiveSmallIntegerField(_("Année"))
    mois = models.PositiveSmallIntegerField(_("Mois"))
    montant_objectif = models.DecimalField(
        _("Montant objectif (GNF)"), max_digits=16, decimal_places=2,
    )
    montant_realise = models.DecimalField(
        _("Montant réalisé (GNF)"), max_digits=16, decimal_places=2, default=0,
    )
    notes = models.TextField(_("Notes"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='objectifs_crees',
    )

    class Meta:
        verbose_name = _("Objectif de vente")
        verbose_name_plural = _("Objectifs de vente")
        ordering = ['-annee', '-mois']
        constraints = [
            models.UniqueConstraint(
                fields=['depot', 'annee', 'mois'],
                name='unique_objectif_depot_mois',
            )
        ]

    def __str__(self):
        return f"Objectif {self.depot} — {self.mois}/{self.annee}"

    @property
    def taux_realisation(self):
        if not self.montant_objectif:
            return 0
        return round(float(self.montant_realise) / float(self.montant_objectif) * 100, 1)


# ── Historique affectations ───────────────────────────────────────────────────
class HistoriqueAffectation(models.Model):
    """Trace les mutations d'un employé entre dépôts."""
    employe = models.ForeignKey(
        Employe, on_delete=models.CASCADE,
        related_name='historique_affectations', verbose_name=_("Employé"),
    )
    depot_ancien = models.ForeignKey(
        'companies.Depot', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='affectations_depart', verbose_name=_("Ancien dépôt"),
    )
    depot_nouveau = models.ForeignKey(
        'companies.Depot', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='affectations_arrivee', verbose_name=_("Nouveau dépôt"),
    )
    motif = models.TextField(_("Motif"), blank=True)
    effectue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='affectations_effectuees', verbose_name=_("Effectué par"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Historique affectation")
        verbose_name_plural = _("Historiques affectations")
        ordering = ['-created_at']

    def __str__(self):
        ancien = self.depot_ancien.code if self.depot_ancien else "—"
        nouveau = self.depot_nouveau.code if self.depot_nouveau else "—"
        return f"{self.employe} : {ancien} → {nouveau}"
