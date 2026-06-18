"""
apps/notifications/signals.py
Déclencheurs automatiques de notifications.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


def _notifier(destinataires, company, type_notif, titre, message, lien=''):
    """Crée des notifications pour une liste d'utilisateurs."""
    from .models import Notification
    for user in destinataires:
        Notification.objects.create(
            destinataire=user,
            company=company,
            type_notification=type_notif,
            titre=titre,
            message=message,
            lien=lien,
        )


def _admins_superviseurs(company):
    """Retourne les admins et superviseurs actifs d'une company."""
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role
    User = get_user_model()
    return User.objects.filter(
        company=company,
        role__in=[Role.ADMIN, Role.SUPERVISEUR],
        is_active=True,
    )


def _gestionnaires_stock(company):
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role
    User = get_user_model()
    return User.objects.filter(
        company=company,
        role=Role.GESTIONNAIRE_STOCK,
        is_active=True,
    )


# ── Stock : seuil d'alerte ────────────────────────────────────────────────────
@receiver(post_save, sender='stocks.StockDepot')
def notifier_seuil_stock(sender, instance, **kwargs):
    if not instance.en_alerte:
        return
    company = instance.company
    destinataires = list(_admins_superviseurs(company)) + list(_gestionnaires_stock(company))
    if not destinataires:
        return
    _notifier(
        destinataires=destinataires,
        company=company,
        type_notif='seuil_stock',
        titre=f"Stock bas — {instance.produit.reference}",
        message=(
            f"Le stock de {instance.produit.nom} dans le dépôt "
            f"{instance.depot.code} est de {instance.quantite} "
            f"(seuil : {instance.produit.seuil_alerte})."
        ),
        lien=f"/stocks/{instance.pk}/",
    )


# ── Caisse : fermeture avec écart ────────────────────────────────────────────
@receiver(post_save, sender='finance.SessionCaisse')
def notifier_ecart_caisse(sender, instance, created, **kwargs):
    from apps.finance.models import SessionCaisse
    if instance.statut != SessionCaisse.Statut.FERMEE:
        return
    if not instance.motif_ecart:
        return
    company = instance.caisse.company
    destinataires = _admins_superviseurs(company)
    _notifier(
        destinataires=destinataires,
        company=company,
        type_notif='ecart_caisse',
        titre=f"Écart de caisse — {instance.caisse.depot.code}",
        message=f"Caisse {instance.caisse.depot.code} fermée avec écart. Motif : {instance.motif_ecart}",
        lien=f"/sessions-caisse/{instance.pk}/",
    )


# ── Mission : litige ─────────────────────────────────────────────────────────
@receiver(post_save, sender='logistique.Mission')
def notifier_mission_litige(sender, instance, **kwargs):
    from apps.logistique.models import Mission
    if instance.statut != Mission.Statut.LITIGE:
        return
    company = instance.company
    destinataires = _admins_superviseurs(company)
    _notifier(
        destinataires=destinataires,
        company=company,
        type_notif='mission_litige',
        titre=f"Mission en litige — {instance.numero}",
        message=f"La mission {instance.numero} est en litige : {instance.motif_litige}",
        lien=f"/missions/{instance.pk}/",
    )


# ── Transfert de stock : réceptionné ─────────────────────────────────────────
@receiver(post_save, sender='stocks.TransfertStock')
def notifier_transfert_receptionne(sender, instance, **kwargs):
    from apps.stocks.models import TransfertStock
    if instance.statut != TransfertStock.Statut.RECU:
        return
    company = instance.company
    destinataires = list(_admins_superviseurs(company)) + list(_gestionnaires_stock(company))
    _notifier(
        destinataires=destinataires,
        company=company,
        type_notif='transfert_valide',
        titre=f"Transfert reçu — {instance.numero}",
        message=(
            f"Le transfert {instance.numero} de {instance.depot_source.code} "
            f"vers {instance.depot_destination.code} a été réceptionné."
        ),
        lien=f"/transferts/{instance.pk}/",
    )


# ── Congé : approuvé ─────────────────────────────────────────────────────────
@receiver(post_save, sender='rh.Conge')
def notifier_conge_approuve(sender, instance, **kwargs):
    from apps.rh.models import Conge
    if instance.statut != Conge.Statut.APPROUVE:
        return
    if not instance.employe.user:
        return
    company = instance.employe.company
    _notifier(
        destinataires=[instance.employe.user],
        company=company,
        type_notif='conge_approuve',
        titre="Congé approuvé",
        message=(
            f"Votre congé du {instance.date_debut} au {instance.date_fin} "
            f"a été approuvé."
        ),
        lien=f"/conges/{instance.pk}/",
    )


# ── Fidélité : seuil de points atteint ───────────────────────────────────────
@receiver(post_save, sender='ventes.Client')
def notifier_seuil_fidelite(sender, instance, **kwargs):
    """Notifie le client quand il atteint un seuil de fidélité."""
    # Seuils : 100, 500, 1000, 5000 points
    seuils = [100, 500, 1000, 5000]
    for seuil in seuils:
        if instance.points_fidelite >= seuil:
            # Vérifier si la notification a déjà été envoyée pour ce seuil
            from .models import Notification
            deja_notifie = Notification.objects.filter(
                destinataire__company=instance.company,
                type_notification='info',  # même type que la notif réellement créée
                lien=f"/clients/{instance.pk}/fidelite/{seuil}/",
            ).exists()
            if deja_notifie:
                continue
            # Chercher un caissier ou admin pour recevoir la notif
            from django.contrib.auth import get_user_model

            from apps.accounts.models import Role
            User = get_user_model()
            destinataires = User.objects.filter(
                company=instance.company,
                role__in=[Role.CAISSIER, Role.ADMIN],
                is_active=True,
            )
            if not destinataires.exists():
                continue
            _notifier(
                destinataires=destinataires,
                company=instance.company,
                type_notif='info',
                titre=f"Seuil fidélité atteint — {instance.nom_complet}",
                message=(
                    f"Le client {instance.nom_complet} a atteint {seuil} points fidélité "
                    f"(total actuel : {instance.points_fidelite} points)."
                ),
                lien=f"/clients/{instance.pk}/fidelite/{seuil}/",
            )
            break  # Notifie seulement le seuil le plus élevé atteint
