"""
apps/rh/views.py
Employés, Présences, Congés, Documents, Objectifs de vente
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasAnyRole, HasRole, IsSuperAdminBlocked

from .models import Conge, Document, Employe, HistoriqueAffectation, ObjectifVente, Presence
from .serializers import (
    CongeSerializer,
    DocumentSerializer,
    EmployeDetailSerializer,
    EmployeListSerializer,
    HistoriqueAffectationSerializer,
    ObjectifVenteSerializer,
    PresenceSerializer,
)


RH_READ = [Role.ADMIN, Role.SUPERVISEUR]
RH_WRITE = [Role.ADMIN]


# ── Employés ──────────────────────────────────────────────────────────────────

@extend_schema(tags=["RH — Employés"])
class EmployeViewSet(CompanyFilterMixin, GenericViewSet,
                     ListModelMixin, RetrieveModelMixin):

    queryset = Employe.objects.select_related('user', 'depot').order_by('nom')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_WRITE)()]

    def get_serializer_class(self):
        return EmployeListSerializer if self.action == 'list' else EmployeDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        statut = self.request.query_params.get('statut')
        depot = self.request.query_params.get('depot')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(nom__icontains=search)
                | Q(prenom__icontains=search)
                | Q(matricule__icontains=search)
            )
        if statut:
            qs = qs.filter(statut=statut)
        if depot:
            qs = qs.filter(depot_id=depot)
        return qs

    def create(self, request, *args, **kwargs):
        s = EmployeDetailSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = EmployeDetailSerializer(obj, data=request.data, partial=True,
                                    context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    @extend_schema(summary="Historique présences d'un employé")
    @action(detail=True, methods=['get'], url_path='presences')
    def presences(self, request, pk=None):
        employe = self.get_object()
        qs = employe.presences.order_by('-date')
        return Response(PresenceSerializer(qs, many=True).data)

    @extend_schema(summary="Historique congés d'un employé")
    @action(detail=True, methods=['get'], url_path='conges')
    def conges(self, request, pk=None):
        employe = self.get_object()
        qs = employe.conges.order_by('-date_debut')
        return Response(CongeSerializer(qs, many=True).data)

    @extend_schema(summary="Documents d'un employé")
    @action(detail=True, methods=['get'], url_path='documents')
    def documents(self, request, pk=None):
        employe = self.get_object()
        qs = employe.documents.order_by('-created_at')
        return Response(DocumentSerializer(qs, many=True).data)

    @extend_schema(summary="Historique des affectations d'un employé")
    @action(detail=True, methods=['get'], url_path='affectations')
    def affectations(self, request, pk=None):
        employe = self.get_object()
        qs = employe.historique_affectations.select_related(
            'depot_ancien', 'depot_nouveau', 'effectue_par'
        ).order_by('-created_at')
        return Response(HistoriqueAffectationSerializer(qs, many=True).data)


# ── Présences ─────────────────────────────────────────────────────────────────

@extend_schema(tags=["RH — Présences"])
class PresenceViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = PresenceSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_WRITE)()]

    def get_queryset(self):
        qs = Presence.objects.select_related('employe', 'enregistre_par').order_by('-date')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(employe__company=company)
        employe = self.request.query_params.get('employe')
        date = self.request.query_params.get('date')
        if employe:
            qs = qs.filter(employe_id=employe)
        if date:
            qs = qs.filter(date=date)
        return qs

    def create(self, request, *args, **kwargs):
        s = PresenceSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = PresenceSerializer(obj, data=request.data, partial=True,
                               context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


# ── Congés ────────────────────────────────────────────────────────────────────

@extend_schema(tags=["RH — Congés"])
class CongeViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = CongeSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_WRITE)()]

    def get_queryset(self):
        qs = Conge.objects.select_related('employe', 'approuve_par').order_by('-date_debut')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(employe__company=company)
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def create(self, request, *args, **kwargs):
        s = CongeSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Approuver un congé")
    @action(detail=True, methods=['post'], url_path='approuver')
    def approuver(self, request, pk=None):
        conge = self.get_object()
        if conge.statut != Conge.Statut.EN_ATTENTE:
            raise ValidationError("Ce congé n'est plus en attente.")
        conge.statut = Conge.Statut.APPROUVE
        conge.approuve_par = request.user
        conge.save(update_fields=['statut', 'approuve_par'])
        return Response(CongeSerializer(conge).data)

    @extend_schema(summary="Refuser un congé")
    @action(detail=True, methods=['post'], url_path='refuser')
    def refuser(self, request, pk=None):
        conge = self.get_object()
        if conge.statut != Conge.Statut.EN_ATTENTE:
            raise ValidationError("Ce congé n'est plus en attente.")
        conge.statut = Conge.Statut.REFUSE
        conge.approuve_par = request.user
        conge.save(update_fields=['statut', 'approuve_par'])
        return Response(CongeSerializer(conge).data)


# ── Documents ─────────────────────────────────────────────────────────────────

@extend_schema(tags=["RH — Documents"])
class DocumentViewSet(CompanyFilterMixin, GenericViewSet,
                      ListModelMixin, RetrieveModelMixin):

    queryset = Document.objects.select_related('employe', 'uploade_par').order_by('-created_at')
    serializer_class = DocumentSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_WRITE)()]

    def get_queryset(self):
        qs = super().get_queryset()
        type_doc = self.request.query_params.get('type_document')
        employe_id = self.request.query_params.get('employe')
        commande_id = self.request.query_params.get('commande')
        mission_id = self.request.query_params.get('mission')
        transfert_id = self.request.query_params.get('transfert')
        search = self.request.query_params.get('search')
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        if type_doc:
            qs = qs.filter(type_document=type_doc)
        if employe_id:
            qs = qs.filter(employe_id=employe_id)
        if commande_id:
            qs = qs.filter(commande_id=commande_id)
        if mission_id:
            qs = qs.filter(mission_id=mission_id)
        if transfert_id:
            qs = qs.filter(transfert_id=transfert_id)
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(titre__icontains=search) | Q(reference_externe__icontains=search)
            )
        if date_debut:
            qs = qs.filter(created_at__date__gte=date_debut)
        if date_fin:
            qs = qs.filter(created_at__date__lte=date_fin)
        return qs

    def create(self, request, *args, **kwargs):
        s = DocumentSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Objectifs de vente ────────────────────────────────────────────────────────

@extend_schema(tags=["RH — Objectifs"])
class ObjectifVenteViewSet(CompanyFilterMixin, GenericViewSet,
                           ListModelMixin, RetrieveModelMixin):

    queryset = ObjectifVente.objects.select_related('depot').order_by('-annee', '-mois')
    serializer_class = ObjectifVenteSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_WRITE)()]

    def create(self, request, *args, **kwargs):
        s = ObjectifVenteSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = ObjectifVenteSerializer(obj, data=request.data, partial=True,
                                    context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)
