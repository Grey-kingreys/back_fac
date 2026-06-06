from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import MissionViewSet, VehiculeViewSet


router = DefaultRouter()
router.register(r'vehicules', VehiculeViewSet, basename='vehicule')
router.register(r'missions', MissionViewSet, basename='mission')

urlpatterns = [
    path('', include(router.urls)),
]
