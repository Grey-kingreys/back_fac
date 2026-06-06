# apps/accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Comptes utilisateurs'

    def ready(self):
        """
        Connecte les signaux d'audit sur tous les modèles sensibles.
        Appelé une seule fois au démarrage de Django.
        """
        from django.apps import apps

        from .signals import connect_audit_signals

        models_to_audit = []

        _try_models = [
            # Accounts & companies
            ('accounts', 'CustomUser'),
            ('companies', 'Zone'),
            ('companies', 'Depot'),
            # Produits
            ('produits', 'Produit'),
            ('produits', 'Fournisseur'),
            ('produits', 'Categorie'),
            # Stocks
            ('stocks', 'TransfertStock'),
            ('stocks', 'MouvementStock'),
            # Ventes
            ('ventes', 'Commande'),
            ('ventes', 'Paiement'),
            ('ventes', 'Client'),
            # Finance
            ('finance', 'TauxChange'),
            ('finance', 'CaissePhysique'),
            ('finance', 'SessionCaisse'),
            ('finance', 'TransactionCaisse'),
            ('finance', 'CompteMobileMoney'),
            ('finance', 'TransactionMobileMoney'),
            # Logistique
            ('logistique', 'Vehicule'),
            ('logistique', 'Mission'),
            # RH
            ('rh', 'Employe'),
            ('rh', 'Conge'),
            ('rh', 'Document'),
        ]

        for app_label, model_name in _try_models:
            try:
                model = apps.get_model(app_label, model_name)
                models_to_audit.append(model)
            except LookupError:
                pass

        if models_to_audit:
            connect_audit_signals(*models_to_audit)
