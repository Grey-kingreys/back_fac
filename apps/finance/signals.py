"""
apps/finance/signals.py
Protection §1 — immuabilité des caisses fermées.
Bloque toute suppression physique de CaissePhysique et CaisseZone,
même via l'admin Django ou le shell, quelle que soit leur statut.
"""

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import CaisseEntreprise, CaissePhysique, CaisseZone


@receiver(pre_delete, sender=CaissePhysique)
def bloquer_suppression_caisse_physique(sender, instance, **kwargs):
    raise Exception(
        f"Suppression interdite — La caisse physique '{instance.nom}' "
        "ne peut pas être supprimée (règle universelle §1 : immuabilité des caisses)."
    )


@receiver(pre_delete, sender=CaisseZone)
def bloquer_suppression_caisse_zone(sender, instance, **kwargs):
    raise Exception(
        f"Suppression interdite — La caisse zone '{instance.nom}' "
        "ne peut pas être supprimée (règle universelle §1 : immuabilité des caisses)."
    )


@receiver(pre_delete, sender=CaisseEntreprise)
def bloquer_suppression_caisse_entreprise(sender, instance, **kwargs):
    raise Exception(
        f"Suppression interdite — La caisse entreprise '{instance.nom}' "
        "ne peut pas être supprimée (règle universelle §1 : immuabilité des caisses)."
    )
