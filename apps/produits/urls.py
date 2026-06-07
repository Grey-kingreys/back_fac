from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    CategorieViewSet,
    CommandeFournisseurViewSet,
    EvaluationFournisseurViewSet,
    FournisseurViewSet,
    MouvementDetteFournisseurViewSet,
    ProduitViewSet,
    UniteViewSet,
)


router = DefaultRouter()
router.register(r'categories', CategorieViewSet, basename='categorie')
router.register(r'unites', UniteViewSet, basename='unite')
router.register(r'fournisseurs', FournisseurViewSet, basename='fournisseur')
router.register(r'produits', ProduitViewSet, basename='produit')
router.register(r'commandes-fournisseurs', CommandeFournisseurViewSet,
                basename='commande-fournisseur')
router.register(r'mouvements-dette', MouvementDetteFournisseurViewSet,
                basename='mouvement-dette')
router.register(r'evaluations-fournisseurs', EvaluationFournisseurViewSet,
                basename='evaluation-fournisseur')

urlpatterns = [
    path('', include(router.urls)),
]
