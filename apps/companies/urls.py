# apps/companies/urls.py
"""
apps/companies/urls.py
Routes complètes : Company (CRUD) + Zones + Dépôts

À inclure dans config/urls.py :
    path("api/", include("apps.companies.urls"))
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ZoneViewSet, DepotViewSet
from .views_company import CompanyListCreateView, CompanyDetailView, CompanyToggleView

# Router pour Zones et Dépôts (ViewSets existants)
router = DefaultRouter()
router.register(r'zones', ZoneViewSet, basename='zone')
router.register(r'depots', DepotViewSet, basename='depot')

urlpatterns = [
    # ── Companies (SuperAdmin / Admin) ────────────────────────────────────
    path('companies/', CompanyListCreateView.as_view(), name='company-list-create'),
    path('companies/<int:pk>/', CompanyDetailView.as_view(), name='company-detail'),
    path('companies/<int:pk>/toggle/', CompanyToggleView.as_view(), name='company-toggle'),

    # ── Zones et Dépôts (filtrés par company) ────────────────────────────
    path('', include(router.urls)),
]