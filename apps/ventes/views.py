"""
apps/ventes/views.py
Clients, Commandes, Paiements, Paramètres fidélité
"""

from decimal import Decimal

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole, IsCompanyMember

from .models import Client, Commande, Paiement, ParametresFidelite
from .serializers import (
    ClientDetailSerializer,
    ClientListSerializer,
    CommandeCreateSerializer,
    CommandeDetailSerializer,
    CommandeListSerializer,
    PaiementInputSerializer,
    ParametresFideliteSerializer,
)
from .services import creer_commande, enregistrer_paiement


def _check_company(request, view, obj):
    if not IsCompanyMember().has_object_permission(request, view, obj):
        raise PermissionDenied("Vous n'avez pas accès à cette ressource.")


class VenteWriteMixin:
    READ_ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.CAISSIER, Role.COMMERCIAL, Role.SUPERADMIN]
    WRITE_ROLES = [Role.ADMIN, Role.CAISSIER, Role.SUPERADMIN]

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(self.READ_ROLES)]
        return [IsAuthenticated(), HasRole(self.WRITE_ROLES)]


# ── Paramètres fidélité ───────────────────────────────────────────────────────

@extend_schema(tags=["Ventes — Fidélité"])
class ParametresFideliteView(APIView):

    def get_permissions(self):
        return [IsAuthenticated(), HasRole([Role.ADMIN, Role.SUPERADMIN])]

    @extend_schema(summary="Lire les paramètres fidélité de l'entreprise")
    def get(self, request):
        company = request.user.company
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)
        params, _ = ParametresFidelite.objects.get_or_create(company=company)
        return Response(ParametresFideliteSerializer(params).data)

    @extend_schema(summary="Mettre à jour les paramètres fidélité")
    def patch(self, request):
        company = request.user.company
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)
        params, _ = ParametresFidelite.objects.get_or_create(company=company)
        s = ParametresFideliteSerializer(params, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


# ── Clients ───────────────────────────────────────────────────────────────────

@extend_schema(tags=["Ventes — Clients"])
class ClientViewSet(VenteWriteMixin, CompanyFilterMixin, GenericViewSet,
                    ListModelMixin, RetrieveModelMixin):

    queryset = Client.objects.order_by('nom')

    def get_serializer_class(self):
        return ClientListSerializer if self.action == 'list' else ClientDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        from django.db.models import Q
        search = self.request.query_params.get('search')
        is_active = self.request.query_params.get('is_active')
        if search:
            qs = qs.filter(
                Q(nom__icontains=search)
                | Q(prenom__icontains=search)
                | Q(telephone__icontains=search)
                | Q(code__icontains=search)
            )
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))
        return qs

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        _check_company(request, self, obj)
        return Response(ClientDetailSerializer(obj, context={'request': request}).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(
            ClientDetailSerializer(s.instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        _check_company(request, self, obj)
        s = self.get_serializer(obj, data=request.data, partial=True,
                                context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(ClientDetailSerializer(obj, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        _check_company(request, self, obj)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Client '{obj.nom_complet}' désactivé."})


# ── Commandes ─────────────────────────────────────────────────────────────────

@extend_schema(tags=["Ventes — Commandes"])
class CommandeViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    VENTE_ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.CAISSIER, Role.SUPERADMIN]

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(self.VENTE_ROLES)]

    def get_serializer_class(self):
        return CommandeListSerializer if self.action == 'list' else CommandeDetailSerializer

    def get_queryset(self):
        qs = Commande.objects.select_related(
            'company', 'depot', 'client', 'caissier'
        ).prefetch_related('lignes__produit', 'paiements').order_by('-created_at')

        user = self.request.user
        if not user.is_superadmin:
            company = user.company
            if not company:
                return qs.none()
            qs = qs.filter(company=company)

        depot = self.request.query_params.get('depot')
        statut = self.request.query_params.get('statut')
        client = self.request.query_params.get('client')
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')

        if depot:
            qs = qs.filter(depot_id=depot)
        if statut:
            qs = qs.filter(statut=statut)
        if client:
            qs = qs.filter(client_id=client)
        if date_debut:
            qs = qs.filter(created_at__date__gte=date_debut)
        if date_fin:
            qs = qs.filter(created_at__date__lte=date_fin)

        return qs

    @extend_schema(summary="Créer une commande")
    def create(self, request, *args, **kwargs):
        s = CommandeCreateSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company
        if not company:
            raise ValidationError("Pas d'entreprise associée.")

        from apps.companies.models import Depot
        try:
            depot = Depot.objects.get(pk=d['depot'], is_active=True)
        except Depot.DoesNotExist:
            raise ValidationError({'depot': "Dépôt introuvable ou inactif."})

        if not request.user.is_superadmin and depot.zone.company != company:
            raise PermissionDenied("Ce dépôt n'appartient pas à votre entreprise.")

        client = None
        if d.get('client'):
            try:
                client = Client.objects.get(pk=d['client'], company=company)
            except Client.DoesNotExist:
                raise ValidationError({'client': "Client introuvable."})

        try:
            commande = creer_commande(
                company=company, depot=depot, caissier=request.user,
                lignes_data=d['lignes'], client=client,
                mode_paiement=d.get('mode_paiement', Commande.ModePaiement.COMPTANT),
                remise=d.get('remise', Decimal('0')),
                points_utilises=d.get('points_utilises', 0),
                notes=d.get('notes', ''),
                montant_paye=d.get('montant_paye', Decimal('0')),
                mode_paiement_initial=d.get('mode_paiement_initial', Paiement.Mode.ESPECES),
                reference_paiement=d.get('reference_paiement', ''),
            )
        except (ValueError, Exception) as e:
            raise ValidationError(str(e))

        return Response(
            CommandeDetailSerializer(commande).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Ajouter un paiement sur une commande")
    @action(detail=True, methods=['post'], url_path='paiement')
    def ajouter_paiement(self, request, pk=None):
        commande = self.get_object()
        s = PaiementInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            enregistrer_paiement(
                commande=commande, montant=d['montant'],
                mode=d['mode'], caissier=request.user,
                reference=d.get('reference', ''),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        commande.refresh_from_db()
        return Response(CommandeDetailSerializer(commande).data)

    @extend_schema(summary="Annuler une commande")
    @action(detail=True, methods=['post'], url_path='annuler')
    def annuler(self, request, pk=None):
        commande = self.get_object()
        if commande.statut == Commande.Statut.ANNULEE:
            raise ValidationError("La commande est déjà annulée.")
        if commande.statut == Commande.Statut.LIVREE:
            raise ValidationError("Impossible d'annuler une commande livrée.")
        commande.statut = Commande.Statut.ANNULEE
        commande.save(update_fields=['statut'])
        return Response(CommandeDetailSerializer(commande).data)
