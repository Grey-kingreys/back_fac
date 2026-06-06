from rest_framework.routers import DefaultRouter

from .views import MouvementStockViewSet, StockDepotViewSet, TransfertStockViewSet


router = DefaultRouter()
router.register(r'stocks', StockDepotViewSet, basename='stock')
router.register(r'mouvements-stock', MouvementStockViewSet, basename='mouvement-stock')
router.register(r'transferts', TransfertStockViewSet, basename='transfert')

urlpatterns = router.urls
