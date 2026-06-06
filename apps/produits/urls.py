from rest_framework.routers import DefaultRouter

from .views import CategorieViewSet, FournisseurViewSet, ProduitViewSet, UniteViewSet


router = DefaultRouter()
router.register(r'categories', CategorieViewSet, basename='categorie')
router.register(r'unites', UniteViewSet, basename='unite')
router.register(r'fournisseurs', FournisseurViewSet, basename='fournisseur')
router.register(r'produits', ProduitViewSet, basename='produit')

urlpatterns = router.urls
