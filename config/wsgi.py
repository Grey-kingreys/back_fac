"""
config/wsgi.py — Gestion Intégrée Multi-Sites
OpenTelemetry est initialisé AVANT le chargement de Django.
"""

import os

from apps.telemetry import setup_tracing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Tracing OpenTelemetry → Tempo (no-op si OTEL_EXPORTER_OTLP_ENDPOINT absent)
setup_tracing()

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
