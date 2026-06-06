"""
apps/logistique/views.py
Véhicules, Missions, GPS
"""

from django.utils import timezone

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole

from .models import LigneMission, Mission, PositionGPS, Vehicule
from .serializers import (
    LigneMissionSerializer,
    MissionCreateSerializer,
    MissionDetailSerializer,
    MissionListSerializer,
    PositionGPSSerializer,
    SignatureArriveeSerializer,
    VehiculeSerializer,
)


LOG_READ = [Role.ADMIN, Role.SUPERVISEUR, Role.CHAUFFEUR, Role.SUPERADMIN]
LOG_WRITE = [Role.ADMIN, Role.SUPERVISEUR, Role.SUPERADMIN]


# ── Véhicules ─────────────────────────────────────────────────────────────────

@extend_schema(tags=["Logistique — Véhicules"])
class VehiculeViewSet(CompanyFilterMixin, GenericViewSet,
                      ListModelMixin, RetrieveModelMixin):

    queryset = Vehicule.objects.order_by('immatriculation')
    serializer_class = VehiculeSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(LOG_READ)]
        return [IsAuthenticated(), HasRole(LOG_WRITE)]

    def create(self, request, *args, **kwargs):
        s = VehiculeSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = VehiculeSerializer(obj, data=request.data, partial=True,
                               context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.statut == Vehicule.Statut.EN_MISSION:
            raise ValidationError("Impossible de désactiver un véhicule en mission.")
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Véhicule '{obj.immatriculation}' désactivé."})


# ── Missions ──────────────────────────────────────────────────────────────────

@extend_schema(tags=["Logistique — Missions"])
class MissionViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(LOG_READ)]

    def get_serializer_class(self):
        return MissionListSerializer if self.action == 'list' else MissionDetailSerializer

    def get_queryset(self):
        qs = Mission.objects.select_related(
            'vehicule', 'chauffeur', 'depot_depart', 'depot_arrivee',
        ).prefetch_related('lignes__produit', 'positions').order_by('-created_at')

        user = self.request.user
        if not user.is_superadmin:
            company = user.company
            if not company:
                return qs.none()
            qs = qs.filter(company=company)
            if user.role == Role.CHAUFFEUR:
                qs = qs.filter(chauffeur=user)

        statut = self.request.query_params.get('statut')
        vehicule = self.request.query_params.get('vehicule')
        chauffeur = self.request.query_params.get('chauffeur')
        if statut:
            qs = qs.filter(statut=statut)
        if vehicule:
            qs = qs.filter(vehicule_id=vehicule)
        if chauffeur:
            qs = qs.filter(chauffeur_id=chauffeur)
        return qs

    @extend_schema(summary="Créer une mission")
    def create(self, request, *args, **kwargs):
        HasRole(LOG_WRITE).has_permission(request, self)
        s = MissionCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company
        if not company:
            raise ValidationError("Pas d'entreprise associée.")

        from apps.companies.models import Depot
        try:
            vehicule = Vehicule.objects.get(pk=d['vehicule'], company=company, is_active=True)
        except Vehicule.DoesNotExist:
            raise ValidationError({'vehicule': "Véhicule introuvable ou inactif."})

        if vehicule.statut == Vehicule.Statut.EN_MISSION:
            raise ValidationError("Ce véhicule est déjà en mission.")

        from apps.accounts.models import User
        try:
            chauffeur = User.objects.get(
                pk=d['chauffeur'], company=company, role=Role.CHAUFFEUR, is_active=True)
        except User.DoesNotExist:
            raise ValidationError({'chauffeur': "Chauffeur introuvable."})

        try:
            depot_depart = Depot.objects.get(pk=d['depot_depart'], is_active=True)
            depot_arrivee = Depot.objects.get(pk=d['depot_arrivee'], is_active=True)
        except Depot.DoesNotExist:
            raise ValidationError("Dépôt(s) introuvable(s) ou inactif(s).")

        transfert = None
        if d.get('transfert_stock'):
            from apps.stocks.models import TransfertStock
            try:
                transfert = TransfertStock.objects.get(
                    pk=d['transfert_stock'], company=company)
            except TransfertStock.DoesNotExist:
                raise ValidationError({'transfert_stock': "Transfert de stock introuvable."})

        mission = Mission.objects.create(
            company=company, vehicule=vehicule, chauffeur=chauffeur,
            depot_depart=depot_depart, depot_arrivee=depot_arrivee,
            date_depart_prevue=d.get('date_depart_prevue'),
            notes=d.get('notes', ''),
            transfert_stock=transfert,
            created_by=request.user,
        )
        for ligne_data in d.get('lignes', []):
            from apps.produits.models import Produit
            try:
                produit = Produit.objects.get(
                    pk=ligne_data['produit'], company=company, is_active=True)
            except Produit.DoesNotExist:
                raise ValidationError(f"Produit #{ligne_data['produit']} introuvable.")
            LigneMission.objects.create(
                mission=mission, produit=produit, quantite=ligne_data['quantite'])

        vehicule.statut = Vehicule.Statut.EN_MISSION
        vehicule.save(update_fields=['statut'])

        return Response(
            MissionDetailSerializer(mission).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Démarrer le chargement")
    @action(detail=True, methods=['post'], url_path='chargement')
    def chargement(self, request, pk=None):
        HasRole(LOG_WRITE).has_permission(request, self)
        mission = self.get_object()
        if mission.statut != Mission.Statut.PLANIFIEE:
            raise ValidationError("La mission doit être à l'état Planifiée.")
        mission.statut = Mission.Statut.CHARGEMENT
        mission.save(update_fields=['statut'])
        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Démarrer le transit")
    @action(detail=True, methods=['post'], url_path='transit')
    def transit(self, request, pk=None):
        mission = self.get_object()
        if mission.statut != Mission.Statut.CHARGEMENT:
            raise ValidationError("La mission doit être à l'état En chargement.")
        mission.statut = Mission.Statut.EN_TRANSIT
        mission.date_depart_reelle = timezone.now()
        mission.save(update_fields=['statut', 'date_depart_reelle'])
        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Signaler l'arrivée avec signature")
    @action(detail=True, methods=['post'], url_path='arrivee')
    def arrivee(self, request, pk=None):
        mission = self.get_object()
        if mission.statut != Mission.Statut.EN_TRANSIT:
            raise ValidationError("La mission doit être en transit.")

        s = SignatureArriveeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        mission.signature_arrivee = d['signature']
        mission.date_arrivee_reelle = timezone.now()

        if d.get('quantites_recues'):
            for item in d['quantites_recues']:
                try:
                    ligne = LigneMission.objects.get(
                        pk=item['ligne_id'], mission=mission)
                    ligne.quantite_recue = item.get('quantite_recue', ligne.quantite)
                    if item.get('observations'):
                        ligne.observations = item['observations']
                    ligne.save()
                except LigneMission.DoesNotExist:
                    pass

        has_litige = any(
            lig.quantite_recue is not None and lig.quantite_recue < lig.quantite
            for lig in mission.lignes.all()
        )
        if has_litige:
            mission.statut = Mission.Statut.LITIGE
            mission.motif_litige = d.get('motif_litige', "Écart de quantité à l'arrivée.")
        else:
            mission.statut = Mission.Statut.ARRIVEE

        mission.save(update_fields=[
            'statut', 'signature_arrivee', 'date_arrivee_reelle', 'motif_litige'])
        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Terminer la mission")
    @action(detail=True, methods=['post'], url_path='terminer')
    def terminer(self, request, pk=None):
        HasRole(LOG_WRITE).has_permission(request, self)
        mission = self.get_object()
        if mission.statut not in (Mission.Statut.ARRIVEE, Mission.Statut.LITIGE):
            raise ValidationError("La mission doit être Arrivée ou en Litige pour être terminée.")
        mission.statut = Mission.Statut.TERMINEE
        mission.save(update_fields=['statut'])

        mission.vehicule.statut = Vehicule.Statut.DISPONIBLE
        mission.vehicule.save(update_fields=['statut'])

        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Annuler une mission")
    @action(detail=True, methods=['post'], url_path='annuler')
    def annuler(self, request, pk=None):
        HasRole(LOG_WRITE).has_permission(request, self)
        mission = self.get_object()
        if mission.statut in (Mission.Statut.TERMINEE, Mission.Statut.ANNULEE):
            raise ValidationError("Impossible d'annuler cette mission.")
        mission.statut = Mission.Statut.ANNULEE
        mission.save(update_fields=['statut'])

        if mission.vehicule.statut == Vehicule.Statut.EN_MISSION:
            mission.vehicule.statut = Vehicule.Statut.DISPONIBLE
            mission.vehicule.save(update_fields=['statut'])

        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Enregistrer la position GPS du véhicule")
    @action(detail=True, methods=['post'], url_path='position')
    def position(self, request, pk=None):
        mission = self.get_object()
        if mission.statut != Mission.Statut.EN_TRANSIT:
            raise ValidationError("Positions GPS uniquement pour les missions en transit.")
        if request.user != mission.chauffeur and not request.user.is_superadmin:
            raise PermissionDenied("Seul le chauffeur peut envoyer sa position.")

        s = PositionGPSSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        pos = PositionGPS.objects.create(mission=mission, **s.validated_data)
        return Response(PositionGPSSerializer(pos).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Lister les positions GPS d'une mission")
    @action(detail=True, methods=['get'], url_path='positions')
    def positions(self, request, pk=None):
        mission = self.get_object()
        qs = mission.positions.order_by('-enregistre_le')
        return Response(PositionGPSSerializer(qs, many=True).data)
