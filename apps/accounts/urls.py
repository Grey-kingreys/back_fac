"""
apps/accounts/urls.py
R1-B07 — Routes CRUD Utilisateurs
À inclure dans config/urls.py : path("api/", include("apps.accounts.urls"))
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views_users import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]