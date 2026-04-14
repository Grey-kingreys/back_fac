"""
apps/companies/urls.py
R1-B08 — Routes CRUD Zones et Dépôts
À inclure dans config/urls.py : path("api/", include("apps.companies.urls"))
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import DepotViewSet, ZoneViewSet

router = DefaultRouter()
router.register(r'zones', ZoneViewSet, basename='zone')
router.register(r'depots', DepotViewSet, basename='depot')

urlpatterns = [
    path('', include(router.urls)),
]
