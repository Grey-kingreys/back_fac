"""
apps/companies/views.py
R1-B08 — CRUD Zones et Dépôts (API)

Zones :
  GET    /api/zones/              — liste paginée (filtrée par company)
  POST   /api/zones/              — création (Admin)
  GET    /api/zones/{id}/         — détail avec dépôts imbriqués
  PATCH  /api/zones/{id}/         — modification partielle (Admin)
  DELETE /api/zones/{id}/         — désactivation soft (Admin)

Dépôts :
  GET    /api/depots/             — liste paginée (filtrée par company)
  POST   /api/depots/             — création (Admin)
  GET    /api/depots/{id}/        — détail
  PATCH  /api/depots/{id}/        — modification partielle (Admin)
  DELETE /api/depots/{id}/        — désactivation soft (Admin)
  GET    /api/depots/{id}/dashboard/ — placeholder (retourne {})
"""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole, IsCompanyMember, IsSuperAdminBlocked  # noqa: F401

from .models import Depot, Zone
from .serializers import (
    DepotCreateUpdateSerializer,
    DepotDetailSerializer,
    DepotListSerializer,
    ZoneCreateUpdateSerializer,
    ZoneDetailSerializer,
    ZoneListSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# Mixin commun : permissions + vérification company
# ─────────────────────────────────────────────────────────────────────────────


class CompanyObjectMixin:
    """
    Mixin partagé par ZoneViewSet et DepotViewSet.
    Gère les permissions par action et la vérification d'isolation company.
    """

    def get_permissions(self):
        # Lecture : admin, superviseur, gestionnaire (ont besoin de voir zones/dépôts)
        read_perms = [
            IsSuperAdminBlocked(),
            HasRole([Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK]),
            IsAuthenticated(),
        ]
        # Écriture : admin uniquement (configuration de l'infrastructure)
        write_perms = [
            IsSuperAdminBlocked(),
            HasRole([Role.ADMIN]),
            IsAuthenticated(),
        ]
        if self.action in ('list', 'retrieve', 'dashboard'):
            return read_perms
        return write_perms

    def _check_company(self, request, instance):
        """Lève 403 si l'objet n'appartient pas à la company de l'user."""
        perm = IsCompanyMember()
        if not perm.has_object_permission(request, self, instance):
            raise PermissionDenied("Vous n'avez pas accès à cette ressource.")


# ─────────────────────────────────────────────────────────────────────────────
# ZONES
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(tags=["Zones"])
class ZoneViewSet(CompanyObjectMixin, CompanyFilterMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin):
    """
    ViewSet de gestion des zones géographiques.
    Filtrées automatiquement par company via CompanyFilterMixin.
    Le superviseur ne voit que sa propre zone (zone_lookup_field='pk').
    """

    queryset = Zone.objects.prefetch_related('depots').order_by('name')
    zone_lookup_field = 'pk'

    def get_serializer_class(self):
        if self.action == 'list':
            return ZoneListSerializer
        if self.action in ('create', 'partial_update'):
            return ZoneCreateUpdateSerializer
        return ZoneDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))
        return qs

    # ── GET /api/zones/ ──────────────────────────────────────────────────────
    @extend_schema(
        summary="Lister les zones",
        parameters=[
            OpenApiParameter('is_active', description='Filtrer par statut (true/false)', required=False),
        ],
        responses={200: ZoneListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # ── GET /api/zones/{id}/ ─────────────────────────────────────────────────
    @extend_schema(
        summary="Détail d'une zone (avec dépôts imbriqués)",
        responses={
            200: ZoneDetailSerializer,
            403: OpenApiResponse(description="Accès refusé"),
            404: OpenApiResponse(description="Zone introuvable"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_company(request, instance)
        return Response(ZoneDetailSerializer(instance).data)

    # ── POST /api/zones/ ─────────────────────────────────────────────────────
    @extend_schema(
        summary="Créer une zone",
        request=ZoneCreateUpdateSerializer,
        responses={
            201: ZoneDetailSerializer,
            400: OpenApiResponse(description="Données invalides"),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        zone = serializer.save()
        return Response(
            ZoneDetailSerializer(zone).data,
            status=status.HTTP_201_CREATED,
        )

    # ── PATCH /api/zones/{id}/ ───────────────────────────────────────────────
    @extend_schema(
        summary="Modifier une zone (partiel)",
        request=ZoneCreateUpdateSerializer,
        responses={
            200: ZoneDetailSerializer,
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Accès refusé"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_company(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        zone = serializer.save()
        return Response(ZoneDetailSerializer(zone).data)

    # ── DELETE /api/zones/{id}/ ──────────────────────────────────────────────
    @extend_schema(
        summary="Désactiver une zone (soft delete)",
        description="Passe is_active à False. Les dépôts liés ne sont pas désactivés automatiquement.",
        responses={
            200: OpenApiResponse(description="Zone désactivée"),
            403: OpenApiResponse(description="Accès refusé"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_company(request, instance)
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(
            {'detail': f"La zone '{instance.name}' a été désactivée."},
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────────────────────────────────────
# DÉPÔTS
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(tags=["Dépôts"])
class DepotViewSet(CompanyObjectMixin, CompanyFilterMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin):
    """
    ViewSet de gestion des dépôts.
    Filtrés automatiquement par company via CompanyFilterMixin.

    Note : CompanyFilterMixin filtre sur le champ `company`.
    Depot n'a pas de FK company directe — on surcharge get_queryset().
    """

    queryset = Depot.objects.select_related('zone', 'zone__company').order_by('zone__name', 'name')

    def get_serializer_class(self):
        if self.action == 'list':
            return DepotListSerializer
        if self.action in ('create', 'partial_update'):
            return DepotCreateUpdateSerializer
        return DepotDetailSerializer

    def get_queryset(self):
        """
        Surcharge complète : on filtre par zone__company au lieu de company
        car Depot n'a pas de FK company directe (c'est une @property).
        """
        qs = Depot.objects.select_related('zone', 'zone__company').order_by('zone__name', 'name')
        user = self.request.user

        if user.is_superadmin:
            return qs

        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(zone__company=company)

        if user.role == Role.SUPERVISEUR:
            if not user.zone:
                return qs.none()
            qs = qs.filter(zone=user.zone)

        # Filtres query params
        zone = self.request.query_params.get('zone')
        is_active = self.request.query_params.get('is_active')

        if zone:
            qs = qs.filter(zone_id=zone)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))

        return qs

    # ── GET /api/depots/ ─────────────────────────────────────────────────────
    @extend_schema(
        summary="Lister les dépôts",
        parameters=[
            OpenApiParameter('zone', description='Filtrer par ID de zone', required=False),
            OpenApiParameter('is_active', description='Filtrer par statut (true/false)', required=False),
        ],
        responses={200: DepotListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # ── GET /api/depots/{id}/ ────────────────────────────────────────────────
    @extend_schema(
        summary="Détail d'un dépôt",
        responses={
            200: DepotDetailSerializer,
            403: OpenApiResponse(description="Accès refusé"),
            404: OpenApiResponse(description="Dépôt introuvable"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_company(request, instance)
        return Response(DepotDetailSerializer(instance).data)

    # ── POST /api/depots/ ────────────────────────────────────────────────────
    @extend_schema(
        summary="Créer un dépôt",
        request=DepotCreateUpdateSerializer,
        responses={
            201: DepotDetailSerializer,
            400: OpenApiResponse(description="Données invalides"),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        depot = serializer.save()
        return Response(
            DepotDetailSerializer(depot).data,
            status=status.HTTP_201_CREATED,
        )

    # ── PATCH /api/depots/{id}/ ──────────────────────────────────────────────
    @extend_schema(
        summary="Modifier un dépôt (partiel)",
        request=DepotCreateUpdateSerializer,
        responses={
            200: DepotDetailSerializer,
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Accès refusé"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_company(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        depot = serializer.save()
        return Response(DepotDetailSerializer(depot).data)

    # ── DELETE /api/depots/{id}/ ─────────────────────────────────────────────
    @extend_schema(
        summary="Désactiver un dépôt (soft delete)",
        description="Passe is_active à False.",
        responses={
            200: OpenApiResponse(description="Dépôt désactivé"),
            403: OpenApiResponse(description="Accès refusé"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_company(request, instance)
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(
            {'detail': f"Le dépôt '{instance.name}' a été désactivé."},
            status=status.HTTP_200_OK,
        )

    # ── GET /api/depots/{id}/dashboard/ ──────────────────────────────────────
    @extend_schema(
        summary="Dashboard temps réel d'un dépôt",
        description="KPIs : stocks critiques, solde caisse, sessions ouvertes, ventes du jour, "
                    "transferts en cours, missions actives.",
    )
    @action(detail=True, methods=['get'], url_path='dashboard')
    def dashboard(self, request, pk=None):
        from decimal import Decimal

        from django.utils import timezone

        instance = self.get_object()
        self._check_company(request, instance)

        today = timezone.now().date()

        # Stocks critiques
        from apps.stocks.models import StockDepot
        stocks_qs = StockDepot.objects.filter(depot=instance).select_related('produit')
        stock_critique = [
            {
                'produit_id': s.produit_id,
                'produit_reference': s.produit.reference,
                'produit_nom': s.produit.nom,
                'quantite': str(s.quantite),
                'seuil_alerte': str(s.produit.seuil_alerte),
            }
            for s in stocks_qs if s.en_alerte
        ]

        # Caisse
        solde_caisse = Decimal('0')
        sessions_ouvertes = 0
        try:
            from apps.finance.models import CaissePhysique, SessionCaisse
            caisse = CaissePhysique.objects.get(depot=instance)
            solde_caisse = caisse.solde_actuel
            sessions_ouvertes = SessionCaisse.objects.filter(
                caisse=caisse,
                statut=SessionCaisse.Statut.OUVERTE,
            ).count()
        except Exception:
            pass

        # Ventes du jour
        from django.db.models import Sum as DjSum

        from apps.ventes.models import Commande
        commandes_jour = Commande.objects.filter(
            depot=instance,
            created_at__date=today,
        ).exclude(statut=Commande.Statut.ANNULEE)
        ventes_du_jour = {
            'count': commandes_jour.count(),
            'montant_ttc': str(
                commandes_jour.aggregate(t=DjSum('montant_ttc'))['t'] or Decimal('0')
            ),
        }

        # Transferts en cours
        from apps.stocks.models import TransfertStock
        transferts_en_cours = TransfertStock.objects.filter(
            depot_source=instance,
            statut=TransfertStock.Statut.EN_TRANSIT,
        ).count()

        # Missions actives
        from apps.logistique.models import Mission
        missions_actives = Mission.objects.filter(
            depot_depart=instance,
            statut__in=[
                Mission.Statut.PLANIFIEE,
                Mission.Statut.CHARGEMENT,
                Mission.Statut.EN_TRANSIT,
            ],
        ).count()

        return Response({
            'depot': {
                'id': instance.pk,
                'code': instance.code,
                'name': instance.name,
            },
            'stock_critique': stock_critique,
            'solde_caisse': str(solde_caisse),
            'sessions_ouvertes': sessions_ouvertes,
            'ventes_du_jour': ventes_du_jour,
            'transferts_en_cours': transferts_en_cours,
            'missions_actives': missions_actives,
        })
