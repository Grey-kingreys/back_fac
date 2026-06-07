from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    ClientViewSet,
    CommandeViewSet,
    DevisViewSet,
    HistoriquePointsViewSet,
    ParametresFideliteView,
    PromotionViewSet,
    RetourCommandeViewSet,
)


router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'commandes', CommandeViewSet, basename='commande')
router.register(r'devis', DevisViewSet, basename='devis')
router.register(r'retours', RetourCommandeViewSet, basename='retour')
router.register(r'historique-points', HistoriquePointsViewSet, basename='historique-points')
router.register(r'promotions', PromotionViewSet, basename='promotion')

urlpatterns = [
    path('', include(router.urls)),
    path('fidelite/parametres/', ParametresFideliteView.as_view(), name='fidelite-parametres'),
]
