from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    AjustementStockViewSet,
    InventaireViewSet,
    MouvementStockViewSet,
    StockDepotViewSet,
    TransfertStockViewSet,
)


router = DefaultRouter()
router.register(r'stocks', StockDepotViewSet, basename='stock')
router.register(r'mouvements-stock', MouvementStockViewSet, basename='mouvement-stock')
router.register(r'transferts', TransfertStockViewSet, basename='transfert')
router.register(r'inventaires', InventaireViewSet, basename='inventaire')
router.register(r'ajustements-stock', AjustementStockViewSet, basename='ajustement-stock')

urlpatterns = [
    path('', include(router.urls)),
]
