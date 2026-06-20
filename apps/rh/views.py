"""
apps/rh/views.py
Employés, Présences, Congés, Documents, Objectifs de vente
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
from apps.accounts.permissions import (
    CompanyFilterMixin, HasAnyRole, HasRole, IsSuperAdminBlocked,
    apply_geo_scope, assert_depot_in_scope,
)

from .models import Conge, Document, Employe, HistoriqueAffectation, ObjectifVente, Presence
from .serializers import (
    CongeDemandeSerializer,
    CongeSerializer,
    DocumentSerializer,
    EmployeDetailSerializer,
    EmployeListSerializer,
    HistoriqueAffectationSerializer,
    ObjectifVenteSerializer,
    PresencePointerSerializer,
    PresenceSerializer,
)
from .utils import haversine_m, point_reference_employe


def _employe_du_user(user):
    """Retourne la fiche Employé liée au compte connecté, ou None."""
    if not user.company_id:
        return None
    return (
        Employe.objects
        .filter(user=user, company=user.company)
        .select_related('depot', 'depot__zone')
        .first()
    )


RH_READ = [Role.ADMIN, Role.SUPERVISEUR]
RH_WRITE = [Role.ADMIN]


# ── Employés ──────────────────────────────────────────────────────────────────

@extend_schema(tags=["RH — Employés"])
class EmployeViewSet(CompanyFilterMixin, GenericViewSet,
                     ListModelMixin, RetrieveModelMixin):

    queryset = Employe.objects.select_related('user', 'depot').order_by('nom')
    zone_lookup_field = 'depot__zone'
    depot_lookup_field = 'depot'

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
        assert_depot_in_scope(request.user, s.validated_data.get('depot'))
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
    # Actions self-service ouvertes à tout employé connecté (hors superadmin).
    SELF_SERVICE_ACTIONS = ('pointer', 'aujourdhui')

    def get_permissions(self):
        if self.action in self.SELF_SERVICE_ACTIONS:
            return [IsAuthenticated(), IsSuperAdminBlocked()]
        if self.action in ('list', 'retrieve', 'recap'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_WRITE)()]

    def get_queryset(self):
        qs = Presence.objects.select_related(
            'employe', 'employe__depot', 'enregistre_par').order_by('-date')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(employe__company=company)
        qs = apply_geo_scope(qs, user, depot_fields='employe__depot', zone_field='employe__depot__zone')
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
        employe = s.validated_data.get('employe')
        assert_depot_in_scope(request.user, getattr(employe, 'depot', None))
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = PresenceSerializer(obj, data=request.data, partial=True,
                               context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    # ── Self-service : pointer sa présence du jour ───────────────────────────
    @extend_schema(summary="Pointer sa présence du jour (self-service)",
                   request=PresencePointerSerializer)
    @action(detail=False, methods=['post'], url_path='pointer')
    def pointer(self, request):
        employe = _employe_du_user(request.user)
        if employe is None:
            raise ValidationError(
                "Aucune fiche employé n'est liée à votre compte. "
                "Contactez votre administrateur.")

        today = timezone.localdate()
        if Presence.objects.filter(employe=employe, date=today).exists():
            raise ValidationError("Vous avez déjà pointé votre présence aujourd'hui.")

        s = PresencePointerSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        lat = s.validated_data['latitude']
        lon = s.validated_data['longitude']

        # Géofencing : comparer au dépôt (sinon zone) de l'employé.
        ref_lat, ref_lon, ref_type = point_reference_employe(employe)
        distance_m = None
        dans_perimetre = None
        if ref_lat is not None:
            distance_m = round(haversine_m(lat, lon, ref_lat, ref_lon))
            rayon = getattr(request.user.company, 'rayon_presence_m', 100) or 100
            dans_perimetre = distance_m <= rayon

        presence = Presence.objects.create(
            employe=employe,
            date=today,
            type_presence=Presence.TypePresence.PRESENT,
            heure_arrivee=timezone.localtime().time(),
            observations=s.validated_data.get('observations', ''),
            latitude=lat,
            longitude=lon,
            distance_m=distance_m,
            dans_perimetre=dans_perimetre,
            reference_geo=ref_type,
            enregistre_par=request.user,
        )
        return Response(PresenceSerializer(presence).data,
                        status=status.HTTP_201_CREATED)

    # ── Self-service : état de mon pointage du jour (pilote le bouton) ────────
    @extend_schema(summary="Mon statut de présence du jour")
    @action(detail=False, methods=['get'], url_path='aujourdhui')
    def aujourdhui(self, request):
        employe = _employe_du_user(request.user)
        if employe is None:
            return Response({
                'a_fiche_employe': False,
                'deja_pointe': False,
                'presence': None,
            })
        today = timezone.localdate()
        presence = Presence.objects.filter(employe=employe, date=today).first()
        return Response({
            'a_fiche_employe': True,
            'deja_pointe': presence is not None,
            'presence': PresenceSerializer(presence).data if presence else None,
        })

    # ── Admin/Superviseur : récap présences/absences d'une journée ───────────
    @extend_schema(summary="Récapitulatif présences/absences du jour (admin/superviseur)")
    @action(detail=False, methods=['get'], url_path='recap')
    def recap(self, request):
        date_str = request.query_params.get('date')
        jour = date_str or timezone.localdate().isoformat()

        # Effectif actif dans le périmètre de l'utilisateur.
        employes = Employe.objects.filter(
            company=request.user.company,
            statut=Employe.Statut.ACTIF,
        ).select_related('depot')
        employes = apply_geo_scope(
            employes, request.user, depot_fields='depot', zone_field='depot__zone')

        presences = {
            p.employe_id: p
            for p in Presence.objects.filter(employe__in=employes, date=jour)
        }

        presents, absents = [], []
        for emp in employes:
            p = presences.get(emp.id)
            ligne = {
                'employe': emp.id,
                'employe_nom': emp.nom_complet,
                'matricule': emp.matricule,
                'depot_nom': emp.depot.name if emp.depot else None,
            }
            if p:
                ligne.update({
                    'heure_arrivee': p.heure_arrivee,
                    'distance_m': p.distance_m,
                    'dans_perimetre': p.dans_perimetre,
                    'reference_geo': p.reference_geo,
                })
                presents.append(ligne)
            else:
                absents.append(ligne)

        return Response({
            'date': jour,
            'effectif': len(presents) + len(absents),
            'nb_presents': len(presents),
            'nb_absents': len(absents),
            'presents': presents,
            'absents': absents,
        })


# ── Congés ────────────────────────────────────────────────────────────────────

@extend_schema(tags=["RH — Congés"])
class CongeViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = CongeSerializer
    # Demander + consulter ses congés : ouvert à tout employé connecté.
    SELF_SERVICE_ACTIONS = ('create', 'mes_demandes')
    # Valider/refuser : prérogative admin + superviseur (validation hiérarchique).
    VALIDATION_ROLES = [Role.ADMIN, Role.SUPERVISEUR]

    def get_permissions(self):
        if self.action in self.SELF_SERVICE_ACTIONS:
            return [IsAuthenticated(), IsSuperAdminBlocked()]
        if self.action in ('approuver', 'refuser'):
            return [IsAuthenticated(), IsSuperAdminBlocked(),
                    HasAnyRole(*self.VALIDATION_ROLES)()]
        # list / retrieve
        return [IsAuthenticated(), IsSuperAdminBlocked()]

    def get_queryset(self):
        qs = Conge.objects.select_related(
            'employe', 'employe__depot', 'demande_par', 'approuve_par'
        ).order_by('-created_at')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(employe__company=company)

        # Admin/superviseur : tout leur périmètre géographique.
        # Autres rôles : uniquement leurs propres demandes.
        if user.role in (Role.ADMIN, Role.SUPERVISEUR):
            qs = apply_geo_scope(
                qs, user, depot_fields='employe__depot', zone_field='employe__depot__zone')
        else:
            qs = qs.filter(employe__user=user)

        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    @extend_schema(summary="Demander un congé (self-service)",
                   request=CongeDemandeSerializer)
    def create(self, request, *args, **kwargs):
        employe = _employe_du_user(request.user)
        if employe is None:
            raise ValidationError(
                "Aucune fiche employé n'est liée à votre compte. "
                "Contactez votre administrateur.")
        s = CongeDemandeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        conge = Conge.objects.create(
            employe=employe,
            statut=Conge.Statut.EN_ATTENTE,
            demande_par=request.user,
            **s.validated_data,
        )
        return Response(CongeSerializer(conge).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Mes demandes de congé")
    @action(detail=False, methods=['get'], url_path='mes-demandes')
    def mes_demandes(self, request):
        qs = Conge.objects.select_related('employe', 'approuve_par').filter(
            employe__user=request.user).order_by('-created_at')
        return Response(CongeSerializer(qs, many=True).data)

    def _verifier_separation(self, conge, user):
        """Anti auto-validation : on ne valide pas sa propre demande."""
        if conge.demande_par_id and conge.demande_par_id == user.id:
            raise PermissionDenied(
                "Vous ne pouvez pas valider votre propre demande de congé.")

    @extend_schema(summary="Approuver un congé (admin/superviseur)")
    @action(detail=True, methods=['post'], url_path='approuver')
    def approuver(self, request, pk=None):
        conge = self.get_object()
        if conge.statut != Conge.Statut.EN_ATTENTE:
            raise ValidationError("Ce congé n'est plus en attente.")
        self._verifier_separation(conge, request.user)
        conge.statut = Conge.Statut.APPROUVE
        conge.approuve_par = request.user
        conge.motif_traitement = request.data.get('motif_traitement', '')
        conge.traite_le = timezone.now()
        conge.save(update_fields=['statut', 'approuve_par', 'motif_traitement', 'traite_le'])
        return Response(CongeSerializer(conge).data)

    @extend_schema(summary="Refuser un congé (admin/superviseur)")
    @action(detail=True, methods=['post'], url_path='refuser')
    def refuser(self, request, pk=None):
        conge = self.get_object()
        if conge.statut != Conge.Statut.EN_ATTENTE:
            raise ValidationError("Ce congé n'est plus en attente.")
        self._verifier_separation(conge, request.user)
        conge.statut = Conge.Statut.REFUSE
        conge.approuve_par = request.user
        conge.motif_traitement = request.data.get('motif_traitement', '')
        conge.traite_le = timezone.now()
        conge.save(update_fields=['statut', 'approuve_par', 'motif_traitement', 'traite_le'])
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
    zone_lookup_field = 'depot__zone'
    depot_lookup_field = 'depot'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*RH_WRITE)()]

    def create(self, request, *args, **kwargs):
        s = ObjectifVenteSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        assert_depot_in_scope(request.user, s.validated_data.get('depot'))
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = ObjectifVenteSerializer(obj, data=request.data, partial=True,
                                    context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)
