from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import ClientViewSet, CommandeViewSet, ParametresFideliteView


router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'commandes', CommandeViewSet, basename='commande')

urlpatterns = [
    path('', include(router.urls)),
    path('fidelite/parametres/', ParametresFideliteView.as_view(), name='fidelite-parametres'),
]
