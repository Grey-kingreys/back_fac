from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    CongeViewSet,
    DocumentViewSet,
    EmployeViewSet,
    ObjectifVenteViewSet,
    PresenceViewSet,
)


router = DefaultRouter()
router.register(r'employes', EmployeViewSet, basename='employe')
router.register(r'presences', PresenceViewSet, basename='presence')
router.register(r'conges', CongeViewSet, basename='conge')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'objectifs-vente', ObjectifVenteViewSet, basename='objectif-vente')

urlpatterns = [
    path('', include(router.urls)),
]
