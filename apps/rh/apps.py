from django.apps import AppConfig


class RhConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rh'
    verbose_name = 'Ressources Humaines'

    def ready(self):
        import apps.rh.signals  # noqa: F401
