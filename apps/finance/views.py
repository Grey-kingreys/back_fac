"""
apps/finance/views.py
Taux de change, Caisses, Sessions, Transactions, Mobile Money
"""

from django.db import models, transaction

from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole

from .models import (
    CaisseEntreprise,
    CaissePhysique,
    CaisseZone,
    CompteMobileMoney,
    DepenseOperationnelle,
    SessionCaisse,
    TauxChange,
    TransactionCaisse,
    TransactionMobileMoney,
    VersementCaisse,
)
from .serializers import (
    CaisseEntrepriseSerializer,
    CaissePhysiqueSerializer,
    CaisseZoneSerializer,
    CompteMobileMoneySerializer,
    DepenseOperationnelleSerializer,
    FermerSessionSerializer,
    OuvrirSessionSerializer,
    SessionCaisseDetailSerializer,
    SessionCaisseListSerializer,
    TauxChangeSerializer,
    TransactionCaisseInputSerializer,
    TransactionMobileMoneyInputSerializer,
    TransactionMobileMoneySerializer,
    VersementCaisseSerializer,
)


FINANCE_READ = [Role.ADMIN, Role.SUPERVISEUR, Role.CAISSIER]
FINANCE_WRITE = [Role.ADMIN]


# ── Taux de change ────────────────────────────────────────────────────────────

@extend_schema(tags=["Finance — Taux de change"])
class TauxChangeViewSet(CompanyFilterMixin, GenericViewSet,
                        ListModelMixin, RetrieveModelMixin):

    queryset = TauxChange.objects.order_by('-created_at')
    serializer_class = TauxChangeSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(FINANCE_READ)]
        return [IsAuthenticated(), HasRole(FINANCE_WRITE)]

    def create(self, request, *args, **kwargs):
        s = TauxChangeSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)


# ── Caisses physiques ─────────────────────────────────────────────────────────

@extend_schema(tags=["Finance — Caisses"])
class CaissePhysiqueViewSet(CompanyFilterMixin, GenericViewSet,
                            ListModelMixin, RetrieveModelMixin):

    queryset = CaissePhysique.objects.select_related('depot').order_by('nom')
    serializer_class = CaissePhysiqueSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(FINANCE_READ)]
        return [IsAuthenticated(), HasRole(FINANCE_WRITE)]

    def create(self, request, *args, **kwargs):
        s = CaissePhysiqueSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)


# ── Sessions caisse ───────────────────────────────────────────────────────────

@extend_schema(tags=["Finance — Sessions"])
class SessionCaisseViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(FINANCE_READ)]

    def get_serializer_class(self):
        return SessionCaisseListSerializer if self.action == 'list' else SessionCaisseDetailSerializer

    def get_queryset(self):
        qs = SessionCaisse.objects.select_related(
            'caisse__depot', 'caissier'
        ).prefetch_related('transactions').order_by('-ouvert_le')

        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(caisse__company=company)

        caisse = self.request.query_params.get('caisse')
        statut = self.request.query_params.get('statut')
        if caisse:
            qs = qs.filter(caisse_id=caisse)
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    @extend_schema(summary="Ouvrir une session de caisse")
    @action(detail=False, methods=['post'], url_path='ouvrir')
    def ouvrir(self, request):
        s = OuvrirSessionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        try:
            caisse = CaissePhysique.objects.get(
                pk=d['caisse'],
                company=request.user.company,
                is_active=True,
            )
        except CaissePhysique.DoesNotExist:
            raise ValidationError({'caisse': "Caisse introuvable ou inactive."})

        session_ouverte = SessionCaisse.objects.filter(
            caisse=caisse, statut=SessionCaisse.Statut.OUVERTE
        ).first()
        if session_ouverte:
            raise ValidationError(
                f"La caisse est déjà ouverte (session #{session_ouverte.pk})."
            )

        session = SessionCaisse.objects.create(
            caisse=caisse,
            caissier=request.user,
            solde_ouverture=d['solde_ouverture'],
            notes=d.get('notes', ''),
        )
        return Response(
            SessionCaisseDetailSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Fermer une session de caisse")
    @action(detail=True, methods=['post'], url_path='fermer')
    def fermer(self, request, pk=None):
        session = self.get_object()
        if session.statut == SessionCaisse.Statut.FERMEE:
            raise ValidationError("Cette session est déjà fermée.")

        s = FermerSessionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        entree_types = [
            TransactionCaisse.TypeTransaction.ENTREE,
            TransactionCaisse.TypeTransaction.VENTE,
            TransactionCaisse.TypeTransaction.APPROVISIONNEMENT,
        ]
        sortie_types = [
            TransactionCaisse.TypeTransaction.SORTIE,
            TransactionCaisse.TypeTransaction.REMBOURSEMENT,
            TransactionCaisse.TypeTransaction.RETRAIT,
        ]
        total_entrees = sum(
            t.montant for t in session.transactions.filter(type_transaction__in=entree_types)
        )
        total_sorties = sum(
            t.montant for t in session.transactions.filter(type_transaction__in=sortie_types)
        )
        session.solde_fermeture_theorique = session.solde_ouverture + total_entrees - total_sorties
        session.save(update_fields=['solde_fermeture_theorique'])

        try:
            session.fermer(
                solde_reel=d['solde_reel'],
                motif_ecart=d.get('motif_ecart', ''),
            )
        except ValueError as e:
            raise ValidationError(str(e))

        session.caisse.solde_actuel = d['solde_reel']
        session.caisse.save(update_fields=['solde_actuel'])

        return Response(SessionCaisseDetailSerializer(session).data)

    @extend_schema(summary="Enregistrer une transaction dans la session")
    @action(detail=True, methods=['post'], url_path='transaction')
    def enregistrer_transaction(self, request, pk=None):
        session = self.get_object()
        if session.statut == SessionCaisse.Statut.FERMEE:
            raise ValidationError("Impossible d'enregistrer sur une session fermée.")

        s = TransactionCaisseInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        entree_types = [
            TransactionCaisse.TypeTransaction.ENTREE,
            TransactionCaisse.TypeTransaction.VENTE,
            TransactionCaisse.TypeTransaction.APPROVISIONNEMENT,
        ]
        with transaction.atomic():
            TransactionCaisse.objects.create(
                session=session, created_by=request.user, **d)
            caisse = session.caisse
            if d['type_transaction'] in entree_types:
                caisse.solde_actuel += d['montant']
            else:
                caisse.solde_actuel -= d['montant']
            caisse.save(update_fields=['solde_actuel'])

        session.refresh_from_db()
        return Response(
            SessionCaisseDetailSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


# ── Mobile Money ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Finance — Mobile Money"])
class CompteMobileMoneyViewSet(CompanyFilterMixin, GenericViewSet,
                               ListModelMixin, RetrieveModelMixin):

    queryset = CompteMobileMoney.objects.select_related('depot').order_by('operateur')
    serializer_class = CompteMobileMoneySerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'transactions'):
            return [IsAuthenticated(), HasRole(FINANCE_READ)]
        return [IsAuthenticated(), HasRole(FINANCE_WRITE)]

    def create(self, request, *args, **kwargs):
        s = CompteMobileMoneySerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Lister les transactions d'un compte Mobile Money")
    @action(detail=True, methods=['get'], url_path='transactions')
    def transactions(self, request, pk=None):
        compte = self.get_object()
        qs = compte.transactions.order_by('-created_at')
        return Response(TransactionMobileMoneySerializer(qs, many=True).data)

    @extend_schema(summary="Enregistrer une transaction Mobile Money")
    @action(detail=True, methods=['post'], url_path='transaction')
    def enregistrer_transaction(self, request, pk=None):
        compte = self.get_object()
        if not compte.is_active:
            raise ValidationError("Ce compte Mobile Money est inactif.")

        s = TransactionMobileMoneyInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        depot_types = [
            TransactionMobileMoney.TypeTransaction.DEPOT,
            TransactionMobileMoney.TypeTransaction.PAIEMENT_RECU,
        ]
        with transaction.atomic():
            tx = TransactionMobileMoney.objects.create(
                compte=compte, created_by=request.user, **d)
            if d['type_transaction'] in depot_types:
                compte.solde += d['montant']
            else:
                compte.solde -= d['montant']
            compte.save(update_fields=['solde'])

        return Response(
            TransactionMobileMoneySerializer(tx).data,
            status=status.HTTP_201_CREATED,
        )


# ── Caisse Zone ───────────────────────────────────────────────────────────────
@extend_schema(tags=["Finance — Caisses Zone"])
class CaisseZoneViewSet(CompanyFilterMixin, GenericViewSet,
                        ListModelMixin, RetrieveModelMixin):

    queryset = CaisseZone.objects.select_related('zone').order_by('nom')
    serializer_class = CaisseZoneSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(FINANCE_READ)]
        return [IsAuthenticated(), HasRole(FINANCE_WRITE)]

    def create(self, request, *args, **kwargs):
        s = CaisseZoneSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)


# ── Caisse Entreprise ─────────────────────────────────────────────────────────
@extend_schema(tags=["Finance — Caisse Entreprise"])
class CaisseEntrepriseViewSet(GenericViewSet, RetrieveModelMixin):
    """Une seule caisse par entreprise — lecture seule via /caisse-entreprise/me/."""

    serializer_class = CaisseEntrepriseSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(FINANCE_READ)]

    def get_queryset(self):
        user = self.request.user
        return CaisseEntreprise.objects.filter(company=user.company)

    @extend_schema(summary="Caisse entreprise de la company connectée")
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        try:
            obj = CaisseEntreprise.objects.get(company=request.user.company)
        except CaisseEntreprise.DoesNotExist:
            return Response({'detail': "Aucune caisse entreprise configurée."}, status=404)
        return Response(CaisseEntrepriseSerializer(obj).data)


# ── Versements inter-niveaux ──────────────────────────────────────────────────
@extend_schema(tags=["Finance — Versements"])
class VersementCaisseViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = VersementCaisseSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(FINANCE_READ)]
        return [IsAuthenticated(), HasRole(FINANCE_WRITE)]

    def get_queryset(self):
        qs = VersementCaisse.objects.select_related(
            'effectue_par', 'recu_par',
            'caisse_source_depot', 'caisse_source_zone',
            'caisse_dest_zone', 'caisse_dest_entreprise',
        ).order_by('-created_at')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(
            models.Q(caisse_source_depot__company=company) |
            models.Q(caisse_source_zone__company=company)
        )
        return qs

    def create(self, request, *args, **kwargs):
        s = VersementCaisseSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        d = s.validated_data

        with transaction.atomic():
            versement = VersementCaisse.objects.create(
                effectue_par=request.user, **d)
            # Mettre à jour les soldes des caisses
            montant = d['montant']
            if d['type_versement'] == VersementCaisse.TypeVersement.DEPOT_VERS_ZONE:
                if d.get('caisse_source_depot'):
                    src = d['caisse_source_depot']
                    src.solde_actuel -= montant
                    src.save(update_fields=['solde_actuel'])
                if d.get('caisse_dest_zone'):
                    dst = d['caisse_dest_zone']
                    dst.solde_actuel += montant
                    dst.save(update_fields=['solde_actuel'])
            elif d['type_versement'] == VersementCaisse.TypeVersement.ZONE_VERS_ENTREPRISE:
                if d.get('caisse_source_zone'):
                    src = d['caisse_source_zone']
                    src.solde_actuel -= montant
                    src.save(update_fields=['solde_actuel'])
                if d.get('caisse_dest_entreprise'):
                    dst = d['caisse_dest_entreprise']
                    dst.solde_actuel += montant
                    dst.save(update_fields=['solde_actuel'])

        return Response(VersementCaisseSerializer(versement).data,
                        status=status.HTTP_201_CREATED)


# ── Dépenses opérationnelles ──────────────────────────────────────────────────
@extend_schema(tags=["Finance — Dépenses"])
class DepenseOperationnelleViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    serializer_class = DepenseOperationnelleSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(FINANCE_READ)]
        return [IsAuthenticated(), HasRole(FINANCE_WRITE)]

    def get_queryset(self):
        qs = DepenseOperationnelle.objects.select_related(
            'company', 'depot', 'enregistre_par'
        ).order_by('-date_depense')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(company=company)
        categorie = self.request.query_params.get('categorie')
        depot = self.request.query_params.get('depot')
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        if categorie:
            qs = qs.filter(categorie=categorie)
        if depot:
            qs = qs.filter(depot_id=depot)
        if date_debut:
            qs = qs.filter(date_depense__gte=date_debut)
        if date_fin:
            qs = qs.filter(date_depense__lte=date_fin)
        return qs

    def create(self, request, *args, **kwargs):
        s = DepenseOperationnelleSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        company = request.user.company
        s.save(company=company, enregistre_par=request.user)
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = DepenseOperationnelleSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Vue consolidée tous niveaux ───────────────────────────────────────────────

@extend_schema(tags=["Finance — Consolidation"])
class ConsolidationCaissesView(APIView):
    """Vue consolidée des soldes de tous les niveaux de caisses."""
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(FINANCE_READ)]

    @extend_schema(summary="Soldes consolidés — tous niveaux de caisses", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        company = request.user.company
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)

        from django.db.models import Sum

        caisses_depot = CaissePhysique.objects.filter(company=company)
        caisses_zone = CaisseZone.objects.filter(company=company)
        caisse_ent = CaisseEntreprise.objects.filter(company=company)

        return Response({
            'caisse_entreprise': [
                {'id': c.pk, 'nom': c.nom, 'solde': str(c.solde_actuel), 'devise': c.devise}
                for c in caisse_ent
            ],
            'caisses_zone': [
                {
                    'id': c.pk, 'nom': c.nom, 'zone': c.zone.name,
                    'solde': str(c.solde_actuel), 'devise': c.devise,
                }
                for c in caisses_zone
            ],
            'caisses_depot': [
                {
                    'id': c.pk, 'nom': c.nom, 'depot': c.depot.name,
                    'solde': str(c.solde_actuel), 'devise': c.devise,
                    'session_ouverte': c.sessions.filter(statut='ouverte').exists(),
                }
                for c in caisses_depot
            ],
            'total_gnf': str(
                (caisses_depot.aggregate(t=Sum('solde_actuel'))['t'] or 0) +
                (caisses_zone.aggregate(t=Sum('solde_actuel'))['t'] or 0) +
                (caisse_ent.aggregate(t=Sum('solde_actuel'))['t'] or 0)
            ),
        })
