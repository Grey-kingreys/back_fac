from django.apps import AppConfig


class StocksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.stocks'
    verbose_name = 'Stocks & Mouvements'

    def ready(self):
        import apps.stocks.signals  # noqa: F401
