# apps/accounts/signals.py
"""
R1-B09 — Signaux Django pour alimenter l'AuditLog.
Enregistre automatiquement les create/update/delete sur :
  - CustomUser
  - Zone (apps.companies)
  - Depot (apps.companies)

Ces signaux sont connectés dans apps/accounts/apps.py via ready().
L'IP est récupérée depuis le thread-local mis en place par AuditMiddleware.
"""

import threading

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

# Thread-local pour stocker l'utilisateur et l'IP courants
# (mis à jour par AuditMiddleware à chaque requête)
_audit_context = threading.local()


def get_current_user():
    return getattr(_audit_context, 'user', None)


def get_current_ip():
    return getattr(_audit_context, 'ip', None)


def set_audit_context(user, ip):
    _audit_context.user = user
    _audit_context.ip = ip


def clear_audit_context():
    _audit_context.user = None
    _audit_context.ip = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize(instance):
    """Sérialise un objet Django en dict JSON-compatible."""
    try:
        data = model_to_dict(instance)
        # Convertir les valeurs non-sérialisables
        for key, val in data.items():
            if hasattr(val, 'pk'):
                data[key] = val.pk
            elif hasattr(val, '__iter__') and not isinstance(val, (str, list, dict)):
                data[key] = list(val)
        return {k: str(v) if not isinstance(v, (int, float, bool, type(None), str)) else v
                for k, v in data.items()}
    except Exception:
        return {}


# Stockage temporaire des états "avant" (pré-save)
_pre_save_states = {}


# ---------------------------------------------------------------------------
# Signaux génériques — connectés dans apps.py
# ---------------------------------------------------------------------------

def handle_pre_save(sender, instance, **kwargs):
    """Capture l'état avant modification."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _pre_save_states[f"{sender.__name__}_{instance.pk}"] = _serialize(old)
        except sender.DoesNotExist:
            pass


def handle_post_save(sender, instance, created, **kwargs):
    """Enregistre un AuditLog après chaque create/update."""
    # Import différé pour éviter les imports circulaires
    from .audit_models import AuditLog

    key = f"{sender.__name__}_{instance.pk}"
    data_before = None if created else _pre_save_states.pop(key, None)
    data_after = _serialize(instance)

    AuditLog.objects.create(
        user=get_current_user(),
        action='create' if created else 'update',
        model_name=sender.__name__,
        object_id=instance.pk,
        data_before=data_before,
        data_after=data_after,
        ip_address=get_current_ip(),
    )


def handle_post_delete(sender, instance, **kwargs):
    """Enregistre un AuditLog après chaque delete."""
    from .audit_models import AuditLog

    AuditLog.objects.create(
        user=get_current_user(),
        action='delete',
        model_name=sender.__name__,
        object_id=instance.pk,
        data_before=_serialize(instance),
        data_after=None,
        ip_address=get_current_ip(),
    )


def connect_audit_signals(*models):
    """
    Connecte les signaux d'audit sur les modèles passés en argument.
    Appelé depuis AccountsConfig.ready().
    """
    for model in models:
        pre_save.connect(handle_pre_save, sender=model)
        post_save.connect(handle_post_save, sender=model)
        post_delete.connect(handle_post_delete, sender=model)