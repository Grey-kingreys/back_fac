# apps/accounts/urls.py
"""
apps/accounts/urls.py
R1-B07 — Routes CRUD Utilisateurs
R1-B09 — Routes Journal d'audit et connexion

À inclure dans config/urls.py : path("api/", include("apps.accounts.urls"))
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_users import UserViewSet
from .audit_views import AuditLogListView, LoginLogListView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),

    # R1-B09 — Journaux d'audit et de connexion
    path('audit-logs/', AuditLogListView.as_view(), name='audit-log-list'),
    path('login-logs/', LoginLogListView.as_view(), name='login-log-list'),
]