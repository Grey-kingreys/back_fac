from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    ConsommationCarburantViewSet,
    DocumentVehiculeViewSet,
    MaintenanceViewSet,
    MissionViewSet,
    PanneViewSet,
    VehiculeViewSet,
)


router = DefaultRouter()
router.register(r'vehicules', VehiculeViewSet, basename='vehicule')
router.register(r'missions', MissionViewSet, basename='mission')
router.register(r'maintenances', MaintenanceViewSet, basename='maintenance')
router.register(r'pannes', PanneViewSet, basename='panne')
router.register(r'documents-vehicule', DocumentVehiculeViewSet, basename='document-vehicule')
router.register(r'carburant', ConsommationCarburantViewSet, basename='carburant')

urlpatterns = [
    path('', include(router.urls)),
]
