"""
apps/rh/signals.py
Signal pre_save sur Employe pour tracer les mutations de dépôt.
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Employe


@receiver(pre_save, sender=Employe)
def tracer_affectation(sender, instance, **kwargs):
    """Si le dépôt de l'employé change, créer un HistoriqueAffectation."""
    if not instance.pk:
        return
    try:
        ancien = Employe.objects.get(pk=instance.pk)
    except Employe.DoesNotExist:
        return
    if ancien.depot_id != instance.depot_id:
        from .models import HistoriqueAffectation
        HistoriqueAffectation.objects.create(
            employe=instance,
            depot_ancien=ancien.depot,
            depot_nouveau=instance.depot,
            motif="Mutation automatique",
            effectue_par=None,
        )
