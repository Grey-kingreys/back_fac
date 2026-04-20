# apps/accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Comptes utilisateurs'

    def ready(self):
        """
        Connecte les signaux d'audit sur les modèles sensibles.
        Appelé une seule fois au démarrage de Django.
        """
        from .signals import connect_audit_signals

        # Import différé des modèles pour éviter les imports circulaires
        from django.apps import apps

        models_to_audit = []

        # CustomUser (toujours disponible)
        try:
            CustomUser = apps.get_model('accounts', 'CustomUser')
            models_to_audit.append(CustomUser)
        except LookupError:
            pass

        # Zone et Depot (apps.companies)
        try:
            Zone = apps.get_model('companies', 'Zone')
            Depot = apps.get_model('companies', 'Depot')
            models_to_audit.extend([Zone, Depot])
        except LookupError:
            pass

        if models_to_audit:
            connect_audit_signals(*models_to_audit)