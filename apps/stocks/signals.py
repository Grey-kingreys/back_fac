"""
apps/stocks/signals.py
Signal post_save sur TransfertStock pour créer automatiquement une Mission
quand le transfert passe en statut EN_TRANSIT.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='stocks.TransfertStock')
def creer_mission_sur_transit(sender, instance, **kwargs):
    """Crée automatiquement une Mission quand un TransfertStock passe EN_TRANSIT."""
    from apps.stocks.models import TransfertStock
    if instance.statut != TransfertStock.Statut.EN_TRANSIT:
        return
    # Vérifier si une mission est déjà liée
    if hasattr(instance, 'mission') and instance.mission is not None:
        return
    from apps.logistique.models import Mission, Vehicule

    # Chercher un véhicule disponible dans la company
    vehicule = Vehicule.objects.filter(
        company=instance.company,
        statut=Vehicule.Statut.DISPONIBLE,
        is_active=True,
    ).first()
    if not vehicule:
        return  # Pas de véhicule disponible, pas de mission auto
    Mission.objects.create(
        company=instance.company,
        vehicule=vehicule,
        chauffeur=vehicule.chauffeur_attitré or instance.utilisateur_envoi,
        depot_depart=instance.depot_source,
        depot_arrivee=instance.depot_destination,
        transfert_stock=instance,
        notes=f"Mission auto-générée pour le transfert {instance.numero}",
        created_by=instance.utilisateur_envoi,
    )
