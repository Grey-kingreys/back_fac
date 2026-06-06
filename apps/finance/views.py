"""
apps/finance/views.py
Taux de change, Caisses, Sessions, Transactions, Mobile Money
"""

from django.db import transaction

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole

from .models import (
    CaissePhysique,
    CompteMobileMoney,
    SessionCaisse,
    TauxChange,
    TransactionCaisse,
    TransactionMobileMoney,
)
from .serializers import (
    CaissePhysiqueSerializer,
    CompteMobileMoneySerializer,
    FermerSessionSerializer,
    OuvrirSessionSerializer,
    SessionCaisseDetailSerializer,
    SessionCaisseListSerializer,
    TauxChangeSerializer,
    TransactionCaisseInputSerializer,
    TransactionMobileMoneyInputSerializer,
    TransactionMobileMoneySerializer,
)


FINANCE_READ = [Role.ADMIN, Role.SUPERVISEUR, Role.CAISSIER, Role.SUPERADMIN]
FINANCE_WRITE = [Role.ADMIN, Role.SUPERADMIN]


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
        if not user.is_superadmin:
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
