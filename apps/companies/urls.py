# apps/companies/urls.py
"""
apps/companies/urls.py
Routes complètes : Company (CRUD) + Zones + Dépôts

À inclure dans config/urls.py :
    path("api/", include("apps.companies.urls"))
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import DepotViewSet, ZoneViewSet
from .views_analytics import (
    AnalyticsFinanceView,
    AnalyticsPerformanceView,
    AnalyticsStockView,
    AnalyticsTvaView,
    AnalyticsVentesView,
    SuperAdminDashboardView,
)
from .views_company import CompanyDetailView, CompanyListCreateView, CompanyToggleView


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

    # ── Analytics ────────────────────────────────────────────────────────
    path('analytics/ventes/', AnalyticsVentesView.as_view(), name='analytics-ventes'),
    path('analytics/stock/', AnalyticsStockView.as_view(), name='analytics-stock'),
    path('analytics/finance/', AnalyticsFinanceView.as_view(), name='analytics-finance'),
    path('analytics/tva/', AnalyticsTvaView.as_view(), name='analytics-tva'),
    path('analytics/performance/', AnalyticsPerformanceView.as_view(),
         name='analytics-performance'),
    path('superadmin/dashboard/', SuperAdminDashboardView.as_view(),
         name='superadmin-dashboard'),
]
