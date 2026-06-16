"""
apps/stocks/views.py
Stocks, Mouvements, Transferts
"""

from django.db import transaction
from django.utils import timezone

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

from .models import AjustementStock, Inventaire, LigneInventaire, MouvementStock, StockDepot, TransfertStock
from .serializers import (
    AjustementStockSerializer,
    EntreeStockSerializer,
    InventaireCreateSerializer,
    InventaireDetailSerializer,
    InventaireListSerializer,
    MouvementStockSerializer,
    SortieStockSerializer,
    StockDepotSerializer,
    TransfertCreateSerializer,
    TransfertDetailSerializer,
    TransfertListSerializer,
    ValiderInventaireSerializer,
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

    STOCK_ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK, Role.CAISSIER]

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(self.STOCK_ROLES)]

    # Override : StockDepot n'a pas de FK company directe
    def get_queryset(self):
        qs = StockDepot.objects.select_related(
            'depot__zone__company', 'produit__unite', 'produit__categorie'
        ).order_by('depot__code', 'produit__nom')

        user = self.request.user
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
            HasRole([Role.ADMIN, Role.GESTIONNAIRE_STOCK]),
        ],
    )
    def entree(self, request):
        s = EntreeStockSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company
        depot = d['depot']
        if depot.zone.company != company:
            raise PermissionDenied("Ce dépôt n'appartient pas à votre entreprise.")
        if d['produit'].company != company:
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
            HasRole([Role.ADMIN, Role.GESTIONNAIRE_STOCK, Role.CAISSIER]),
        ],
    )
    def sortie(self, request):
        s = SortieStockSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company
        depot = d['depot']
        if depot.zone.company != company:
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

    ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK]

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(self.ROLES)]

    def get_queryset(self):
        qs = MouvementStock.objects.select_related(
            'depot__zone__company', 'produit', 'utilisateur'
        ).order_by('-created_at')

        user = self.request.user
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

    ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK]
    WRITE_ROLES = [Role.ADMIN, Role.GESTIONNAIRE_STOCK]

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(self.ROLES)]
        return [IsAuthenticated(), HasRole(self.WRITE_ROLES)]

    def get_queryset(self):
        qs = TransfertStock.objects.select_related(
            'company', 'depot_source', 'depot_destination'
        ).prefetch_related('lignes__produit').order_by('-created_at')

        user = self.request.user
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


# ── Inventaires ───────────────────────────────────────────────────────────────
@extend_schema(tags=["Stocks — Inventaires"])
class InventaireViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK]
    WRITE_ROLES = [Role.ADMIN, Role.SUPERVISEUR]
    CREATE_ROLES = [Role.ADMIN, Role.GESTIONNAIRE_STOCK]

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(self.ROLES)]

    def get_serializer_class(self):
        return InventaireListSerializer if self.action == 'list' else InventaireDetailSerializer

    def get_queryset(self):
        qs = Inventaire.objects.select_related(
            'depot__zone__company', 'cree_par'
        ).prefetch_related('lignes__produit').order_by('-created_at')
        user = self.request.user
        if not user.company:
            return qs.none()
        qs = qs.filter(company=user.company)
        depot = self.request.query_params.get('depot')
        statut = self.request.query_params.get('statut')
        if depot:
            qs = qs.filter(depot_id=depot)
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def create(self, request, *args, **kwargs):
        if not HasRole(self.CREATE_ROLES).has_permission(request, self):
            raise PermissionDenied("Droits insuffisants pour créer un inventaire.")
        s = InventaireCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        depot = d['depot']
        company = request.user.company
        if depot.zone.company != company:
            raise PermissionDenied("Ce dépôt n'appartient pas à votre entreprise.")

        with transaction.atomic():
            inventaire = Inventaire.objects.create(
                company=company,
                depot=depot,
                notes=d.get('notes', ''),
                cree_par=request.user,
            )
            # Créer les lignes depuis les stocks actuels
            stocks = StockDepot.objects.filter(depot=depot).select_related('produit')
            for stock in stocks:
                LigneInventaire.objects.create(
                    inventaire=inventaire,
                    produit=stock.produit,
                    quantite_theorique=stock.quantite,
                )
        return Response(InventaireDetailSerializer(inventaire).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(summary="Valider un inventaire — crée les mouvements de correction")
    @action(detail=True, methods=['post'], url_path='valider')
    def valider(self, request, pk=None):
        if not HasRole(self.WRITE_ROLES).has_permission(request, self):
            raise PermissionDenied("Droits insuffisants pour valider un inventaire.")
        inventaire = self.get_object()
        if inventaire.statut != Inventaire.Statut.EN_COURS:
            raise ValidationError("Seul un inventaire en cours peut être validé.")

        s = ValiderInventaireSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        lignes_data = s.validated_data['lignes']

        with transaction.atomic():
            for item in lignes_data:
                ligne_id = item.get('ligne_id')
                qte_comptee = item.get('quantite_comptee')
                try:
                    ligne = inventaire.lignes.get(pk=ligne_id)
                except LigneInventaire.DoesNotExist:
                    continue
                if qte_comptee is None:
                    continue
                ligne.quantite_comptee = qte_comptee
                ligne.save(update_fields=['quantite_comptee'])

                ecart = qte_comptee - ligne.quantite_theorique
                if ecart != 0:
                    stock, _ = StockDepot.objects.get_or_create(
                        depot=inventaire.depot, produit=ligne.produit,
                        defaults={'quantite': 0},
                    )
                    avant = stock.quantite
                    stock.quantite += ecart
                    stock.save(update_fields=['quantite'])
                    MouvementStock.objects.create(
                        depot=inventaire.depot,
                        produit=ligne.produit,
                        type_mouvement=MouvementStock.TypeMouvement.INVENTAIRE,
                        quantite=abs(ecart),
                        quantite_avant=avant,
                        quantite_apres=stock.quantite,
                        reference_doc=inventaire.numero,
                        motif=f"Correction inventaire {inventaire.numero}",
                        utilisateur=request.user,
                    )

            inventaire.statut = Inventaire.Statut.VALIDE
            inventaire.valide_par = request.user
            inventaire.valide_le = timezone.now()
            inventaire.save(update_fields=['statut', 'valide_par', 'valide_le'])

        return Response(InventaireDetailSerializer(inventaire).data)


# ── Ajustements de stock ─���──────────────────────────────────────────────────��─
@extend_schema(tags=["Stocks — Ajustements"])
class AjustementStockViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = AjustementStockSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasRole([
            Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK
        ])]

    def get_queryset(self):
        qs = AjustementStock.objects.select_related(
            'depot__zone__company', 'produit', 'demande_par'
        ).order_by('-created_at')
        user = self.request.user
        if not user.company:
            return qs.none()
        qs = qs.filter(company=user.company)
        statut = self.request.query_params.get('statut')
        depot = self.request.query_params.get('depot')
        if statut:
            qs = qs.filter(statut=statut)
        if depot:
            qs = qs.filter(depot_id=depot)
        return qs

    def create(self, request, *args, **kwargs):
        if not HasRole([Role.ADMIN, Role.GESTIONNAIRE_STOCK]).has_permission(request, self):
            raise PermissionDenied("Droits insuffisants pour créer un ajustement.")
        s = AjustementStockSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company
        if d['depot'].zone.company != company:
            raise PermissionDenied("Ce dépôt n'appartient pas à votre entreprise.")
        ajustement = AjustementStock.objects.create(
            company=company, demande_par=request.user, **d)
        return Response(AjustementStockSerializer(ajustement).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(summary="Approuver un ajustement de stock")
    @action(detail=True, methods=['post'], url_path='approuver')
    def approuver(self, request, pk=None):
        if not HasRole([Role.ADMIN, Role.SUPERVISEUR]).has_permission(request, self):
            raise PermissionDenied("Droits insuffisants.")
        ajustement = self.get_object()
        if ajustement.statut != AjustementStock.Statut.EN_ATTENTE:
            raise ValidationError("Seul un ajustement en attente peut être approuvé.")

        with transaction.atomic():
            stock, _ = StockDepot.objects.get_or_create(
                depot=ajustement.depot, produit=ajustement.produit,
                defaults={'quantite': 0},
            )
            avant = stock.quantite
            stock.quantite += ajustement.quantite
            stock.save(update_fields=['quantite'])
            MouvementStock.objects.create(
                depot=ajustement.depot,
                produit=ajustement.produit,
                type_mouvement=MouvementStock.TypeMouvement.AJUSTEMENT,
                quantite=abs(ajustement.quantite),
                quantite_avant=avant,
                quantite_apres=stock.quantite,
                motif=ajustement.motif,
                utilisateur=request.user,
            )
            ajustement.statut = AjustementStock.Statut.APPROUVE
            ajustement.traite_par = request.user
            ajustement.traite_le = timezone.now()
            ajustement.save(update_fields=['statut', 'traite_par', 'traite_le'])

        return Response(AjustementStockSerializer(ajustement).data)

    @extend_schema(summary="Refuser un ajustement de stock")
    @action(detail=True, methods=['post'], url_path='refuser')
    def refuser(self, request, pk=None):
        if not HasRole([Role.ADMIN, Role.SUPERVISEUR]).has_permission(request, self):
            raise PermissionDenied("Droits insuffisants.")
        ajustement = self.get_object()
        if ajustement.statut != AjustementStock.Statut.EN_ATTENTE:
            raise ValidationError("Seul un ajustement en attente peut être refusé.")
        ajustement.statut = AjustementStock.Statut.REFUSE
        ajustement.traite_par = request.user
        ajustement.traite_le = timezone.now()
        ajustement.save(update_fields=['statut', 'traite_par', 'traite_le'])
        return Response(AjustementStockSerializer(ajustement).data)
