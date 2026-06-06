from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    CaissePhysiqueViewSet,
    CompteMobileMoneyViewSet,
    SessionCaisseViewSet,
    TauxChangeViewSet,
)


router = DefaultRouter()
router.register(r'taux-change', TauxChangeViewSet, basename='taux-change')
router.register(r'caisses', CaissePhysiqueViewSet, basename='caisse')
router.register(r'sessions-caisse', SessionCaisseViewSet, basename='session-caisse')
router.register(r'comptes-mobile-money', CompteMobileMoneyViewSet, basename='compte-mobile-money')

urlpatterns = [
    path('', include(router.urls)),
]
