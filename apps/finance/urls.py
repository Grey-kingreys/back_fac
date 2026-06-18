from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    CaisseEntrepriseViewSet,
    CaissePhysiqueViewSet,
    CaisseZoneViewSet,
    CompteMobileMoneyViewSet,
    ConfigurationCaisseView,
    ConsolidationCaissesView,
    DepenseOperationnelleViewSet,
    SessionCaisseViewSet,
    TauxChangeViewSet,
    VersementCaisseViewSet,
)


router = DefaultRouter()
router.register(r'taux-change', TauxChangeViewSet, basename='taux-change')
router.register(r'caisses', CaissePhysiqueViewSet, basename='caisse')
router.register(r'caisses-zone', CaisseZoneViewSet, basename='caisse-zone')
router.register(r'caisse-entreprise', CaisseEntrepriseViewSet, basename='caisse-entreprise')
router.register(r'versements-caisse', VersementCaisseViewSet, basename='versement-caisse')
router.register(r'sessions-caisse', SessionCaisseViewSet, basename='session-caisse')
router.register(r'comptes-mobile-money', CompteMobileMoneyViewSet, basename='compte-mobile-money')
router.register(r'depenses', DepenseOperationnelleViewSet, basename='depense')

urlpatterns = [
    path('caisses/consolidation/', ConsolidationCaissesView.as_view(), name='caisses-consolidation'),
    path('configuration-caisses/', ConfigurationCaisseView.as_view(), name='configuration-caisses'),
    path('', include(router.urls)),
]
