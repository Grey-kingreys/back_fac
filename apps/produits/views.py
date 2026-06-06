"""
apps/produits/views.py
CRUD : Categorie, Unite, Fournisseur, Produit
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole, IsCompanyMember

from .models import Categorie, Fournisseur, Produit, Unite
from .serializers import (
    CategorieSerializer,
    FournisseurDetailSerializer,
    FournisseurListSerializer,
    ProduitDetailSerializer,
    ProduitListSerializer,
    UniteSerializer,
)


class CompanyWriteMixin:
    """Permissions : lecture large, écriture admin+."""

    READ_ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK,
                  Role.COMMERCIAL, Role.CAISSIER, Role.SUPERADMIN]
    WRITE_ROLES = [Role.ADMIN, Role.SUPERADMIN]

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'stock'):
            return [IsAuthenticated(), HasRole(self.READ_ROLES)]
        return [IsAuthenticated(), HasRole(self.WRITE_ROLES)]

    def _check_company(self, request, instance):
        if not IsCompanyMember().has_object_permission(request, self, instance):
            raise PermissionDenied("Vous n'avez pas accès à cette ressource.")


# ── Catégories ────────────────────────────────────────────────────────────────

@extend_schema(tags=["Produits — Catégories"])
class CategorieViewSet(CompanyWriteMixin, CompanyFilterMixin,
                       GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Categorie.objects.prefetch_related('produits').order_by('name')
    serializer_class = CategorieSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        v = self.request.query_params.get('is_active')
        if v is not None:
            qs = qs.filter(is_active=v.lower() in ('true', '1'))
        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        return Response(self.get_serializer(obj).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        s = self.get_serializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Catégorie '{obj.name}' désactivée."})


# ── Unités ────────────────────────────────────────────────────────────────────

@extend_schema(tags=["Produits — Unités"])
class UniteViewSet(CompanyWriteMixin, CompanyFilterMixin,
                   GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Unite.objects.order_by('name')
    serializer_class = UniteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        v = self.request.query_params.get('is_active')
        if v is not None:
            qs = qs.filter(is_active=v.lower() in ('true', '1'))
        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        return Response(self.get_serializer(obj).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        s = self.get_serializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Unité '{obj.name}' désactivée."})


# ── Fournisseurs ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Fournisseurs"])
class FournisseurViewSet(CompanyWriteMixin, CompanyFilterMixin,
                         GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Fournisseur.objects.order_by('nom')

    def get_serializer_class(self):
        return FournisseurListSerializer if self.action == 'list' else FournisseurDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        v = self.request.query_params.get('is_active')
        search = self.request.query_params.get('search')
        if v is not None:
            qs = qs.filter(is_active=v.lower() in ('true', '1'))
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(nom__icontains=search) | Q(code__icontains=search))
        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        return Response(FournisseurDetailSerializer(obj, context={'request': request}).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(
            FournisseurDetailSerializer(s.instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        s = self.get_serializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(FournisseurDetailSerializer(obj, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Fournisseur '{obj.nom}' désactivé."})


# ── Produits ──────────────────────────────────────────────────────────────────

@extend_schema(tags=["Produits"])
class ProduitViewSet(CompanyWriteMixin, CompanyFilterMixin,
                     GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Produit.objects.select_related(
        'categorie', 'unite', 'fournisseur_principal'
    ).order_by('nom')

    def get_serializer_class(self):
        return ProduitListSerializer if self.action == 'list' else ProduitDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        from django.db.models import Q
        v = self.request.query_params.get('is_active')
        cat = self.request.query_params.get('categorie')
        search = self.request.query_params.get('search')
        if v is not None:
            qs = qs.filter(is_active=v.lower() in ('true', '1'))
        if cat:
            qs = qs.filter(categorie_id=cat)
        if search:
            qs = qs.filter(Q(nom__icontains=search) | Q(reference__icontains=search))
        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        return Response(ProduitDetailSerializer(obj, context={'request': request}).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(
            ProduitDetailSerializer(s.instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        s = self.get_serializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(ProduitDetailSerializer(obj, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Produit '{obj.nom}' désactivé."})

    @extend_schema(summary="Stock par dépôt pour un produit")
    @action(detail=True, methods=['get'], url_path='stock')
    def stock(self, request, pk=None):
        from apps.stocks.models import StockDepot
        obj = self.get_object()
        self._check_company(request, obj)
        stocks = StockDepot.objects.filter(produit=obj).select_related('depot__zone')
        return Response({
            'produit_id': obj.pk,
            'stocks': [
                {
                    'depot_id': s.depot_id,
                    'depot_code': s.depot.code,
                    'depot_nom': s.depot.name,
                    'zone_nom': s.depot.zone.name,
                    'quantite': s.quantite,
                }
                for s in stocks
            ],
        })
