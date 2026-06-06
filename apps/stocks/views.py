"""
apps/stocks/views.py
Stocks, Mouvements, Transferts
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole, IsCompanyMember

from .models import MouvementStock, StockDepot, TransfertStock
from .serializers import (
    EntreeStockSerializer,
    MouvementStockSerializer,
    SortieStockSerializer,
    StockDepotSerializer,
    TransfertCreateSerializer,
    TransfertDetailSerializer,
    TransfertListSerializer,
)
from .services import (
    creer_transfert,
    entree_stock,
    expedier_transfert,
    receptionner_transfert,
    sortie_stock,
)


def _check_company(request, view, obj):
    if not IsCompanyMember().has_object_permission(request, view, obj):
        raise PermissionDenied("Vous n'avez pas accès à cette ressource.")


# ── Stocks par dépôt ──────────────────────────────────────────────────────────

@extend_schema(tags=["Stocks"])
class StockDepotViewSet(CompanyFilterMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin):
    """Lecture seule — les modifications se font via entrée/sortie."""
    serializer_class = StockDepotSerializer

    STOCK_ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK,
                   Role.CAISSIER, Role.SUPERADMIN]

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(self.STOCK_ROLES)]

    # Override : StockDepot n'a pas de FK company directe
    def get_queryset(self):
        qs = StockDepot.objects.select_related(
            'depot__zone__company', 'produit__unite', 'produit__categorie'
        ).order_by('depot__code', 'produit__nom')

        user = self.request.user
        if not user.is_superadmin:
            company = user.company
            if not company:
                return qs.none()
            qs = qs.filter(depot__zone__company=company)

        depot = self.request.query_params.get('depot')
        produit = self.request.query_params.get('produit')
        alerte = self.request.query_params.get('alerte')

        if depot:
            qs = qs.filter(depot_id=depot)
        if produit:
            qs = qs.filter(produit_id=produit)
        if alerte == 'true':
            from django.db.models import F
            qs = qs.filter(quantite__lte=F('produit__seuil_alerte'))

        return qs

    @extend_schema(
        summary="Lister les niveaux de stock",
        parameters=[
            OpenApiParameter('depot', description='Filtrer par dépôt'),
            OpenApiParameter('produit', description='Filtrer par produit'),
            OpenApiParameter('alerte', description='true = uniquement les stocks en alerte'),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Détail stock d'un produit dans un dépôt")
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        _check_company(request, self, obj)
        return Response(StockDepotSerializer(obj).data)

    @extend_schema(summary="Enregistrer une entrée de stock")
    @action(
        detail=False, methods=['post'], url_path='entree',
        permission_classes=[
            IsAuthenticated,
            HasRole([Role.ADMIN, Role.GESTIONNAIRE_STOCK, Role.SUPERADMIN]),
        ],
    )
    def entree(self, request):
        s = EntreeStockSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company
        depot = d['depot']
        if not request.user.is_superadmin and depot.zone.company != company:
            raise PermissionDenied("Ce dépôt n'appartient pas à votre entreprise.")
        if not request.user.is_superadmin and d['produit'].company != company:
            raise PermissionDenied("Ce produit n'appartient pas à votre entreprise.")
        try:
            mvt = entree_stock(
                depot=depot, produit=d['produit'],
                quantite=d['quantite'], utilisateur=request.user,
                reference_doc=d.get('reference_doc', ''),
                motif=d.get('motif', ''),
                numero_lot=d.get('numero_lot', ''),
                date_expiration=d.get('date_expiration'),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(MouvementStockSerializer(mvt).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Enregistrer une sortie de stock")
    @action(
        detail=False, methods=['post'], url_path='sortie',
        permission_classes=[
            IsAuthenticated,
            HasRole([Role.ADMIN, Role.GESTIONNAIRE_STOCK, Role.CAISSIER, Role.SUPERADMIN]),
        ],
    )
    def sortie(self, request):
        s = SortieStockSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company
        depot = d['depot']
        if not request.user.is_superadmin and depot.zone.company != company:
            raise PermissionDenied("Ce dépôt n'appartient pas à votre entreprise.")
        try:
            mvt = sortie_stock(
                depot=depot, produit=d['produit'],
                quantite=d['quantite'], utilisateur=request.user,
                reference_doc=d.get('reference_doc', ''),
                motif=d.get('motif', ''),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(MouvementStockSerializer(mvt).data, status=status.HTTP_201_CREATED)


# ── Mouvements ────────────────────────────────────────────────────────────────

@extend_schema(tags=["Stocks — Mouvements"])
class MouvementStockViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    serializer_class = MouvementStockSerializer

    ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK, Role.SUPERADMIN]

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(self.ROLES)]

    def get_queryset(self):
        qs = MouvementStock.objects.select_related(
            'depot__zone__company', 'produit', 'utilisateur'
        ).order_by('-created_at')

        user = self.request.user
        if not user.is_superadmin:
            company = user.company
            if not company:
                return qs.none()
            qs = qs.filter(depot__zone__company=company)

        depot = self.request.query_params.get('depot')
        produit = self.request.query_params.get('produit')
        type_mvt = self.request.query_params.get('type')
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')

        if depot:
            qs = qs.filter(depot_id=depot)
        if produit:
            qs = qs.filter(produit_id=produit)
        if type_mvt:
            qs = qs.filter(type_mouvement=type_mvt)
        if date_debut:
            qs = qs.filter(created_at__date__gte=date_debut)
        if date_fin:
            qs = qs.filter(created_at__date__lte=date_fin)

        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


# ── Transferts ────────────────────────────────────────────────────────────────

@extend_schema(tags=["Stocks — Transferts"])
class TransfertStockViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK, Role.SUPERADMIN]
    WRITE_ROLES = [Role.ADMIN, Role.GESTIONNAIRE_STOCK, Role.SUPERADMIN]

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(self.ROLES)]
        return [IsAuthenticated(), HasRole(self.WRITE_ROLES)]

    def get_queryset(self):
        qs = TransfertStock.objects.select_related(
            'company', 'depot_source', 'depot_destination'
        ).prefetch_related('lignes__produit').order_by('-created_at')

        user = self.request.user
        if not user.is_superadmin:
            company = user.company
            if not company:
                return qs.none()
            qs = qs.filter(company=company)

        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def get_serializer_class(self):
        return TransfertListSerializer if self.action == 'list' else TransfertDetailSerializer

    @extend_schema(summary="Lister les transferts de stock")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Détail d'un transfert")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Créer un transfert (brouillon)")
    def create(self, request, *args, **kwargs):
        s = TransfertCreateSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company

        if not request.user.is_superadmin:
            for depot in [d['depot_source'], d['depot_destination']]:
                if depot.zone.company != company:
                    raise PermissionDenied(f"Le dépôt {depot.code} n'appartient pas à votre entreprise.")
            for ligne in d['lignes']:
                if ligne['produit'].company != company:
                    raise PermissionDenied(f"Le produit {ligne['produit'].reference} n'appartient pas à votre entreprise.")

        lignes_data = [
            {
                'produit': lig['produit'],
                'quantite_envoyee': lig['quantite_envoyee'],
                'notes': lig.get('notes', ''),
            }
            for lig in d['lignes']
        ]
        try:
            transfert = creer_transfert(
                company=company or request.user.company,
                depot_source=d['depot_source'],
                depot_destination=d['depot_destination'],
                lignes_data=lignes_data,
                utilisateur=request.user,
                notes=d.get('notes', ''),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(TransfertDetailSerializer(transfert).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(summary="Expédier un transfert (→ en transit)")
    @action(detail=True, methods=['post'], url_path='expedier')
    def expedier(self, request, pk=None):
        obj = self.get_object()
        try:
            expedier_transfert(obj, request.user)
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(TransfertDetailSerializer(obj).data)

    @extend_schema(summary="Réceptionner un transfert")
    @action(detail=True, methods=['post'], url_path='receptionner')
    def receptionner(self, request, pk=None):
        obj = self.get_object()
        lignes_recues = request.data.get('lignes', [])
        try:
            receptionner_transfert(obj, lignes_recues, request.user)
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(TransfertDetailSerializer(obj).data)

    @extend_schema(summary="Annuler un transfert (brouillon seulement)")
    @action(detail=True, methods=['post'], url_path='annuler')
    def annuler(self, request, pk=None):
        obj = self.get_object()
        if obj.statut not in (TransfertStock.Statut.BROUILLON,):
            raise ValidationError("Seul un transfert en brouillon peut être annulé.")
        obj.statut = TransfertStock.Statut.ANNULE
        obj.save(update_fields=['statut'])
        return Response(TransfertDetailSerializer(obj).data)
