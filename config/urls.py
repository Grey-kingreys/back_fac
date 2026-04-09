"""
config/urls.py
URLs racine — Application Gestion Intégrée Multi-Sites
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin Django
    path("admin/", admin.site.urls),

    path("api/auth/", include("apps.accounts.urls_auth")),

    # --- Documentation API ---
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # --- Apps métier (à décommenter au fur et à mesure) ---
    # path("api/", include("apps.accounts.urls")),
    # path("api/", include("apps.entreprises.urls")),
    # path("api/", include("apps.zones.urls")),
    # path("api/", include("apps.produits.urls")),
    # path("api/", include("apps.stocks.urls")),
    # path("api/", include("apps.ventes.urls")),
    # path("api/", include("apps.finance.urls")),
    # path("api/", include("apps.logistique.urls")),
    # path("api/", include("apps.rh.urls")),
]

# Servir les fichiers médias en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
