"""
apps/finance/views.py
Taux de change, Caisses, Sessions, Transactions, Mobile Money
"""

from django.db import models, transaction

from drf_spectacular.openapi import OpenApiTypes
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
from apps.accounts.permissions import CompanyFilterMixin, HasAnyRole, HasRole, IsSuperAdminBlocked

from .models import (
    CaisseEntreprise,
    CaissePhysique,
    CaisseZone,
    CompteMobileMoney,
    ConfigurationCaisse,
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
    ConfigurationCaisseSerializer,
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


# ── Configuration des caisses (durées de période) ─────────────────────────────
@extend_schema(tags=["Finance — Configuration"])
class ConfigurationCaisseView(APIView):
    """
    Configuration des durées de période des caisses (admin).
    GET  : lecture seule (tous les rôles finance).
    PATCH: modification (admin uniquement) — règle session < dépôt < zone.
    """

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_WRITE)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]

    def _get_or_create_config(self, company):
        config, _created = ConfigurationCaisse.objects.get_or_create(company=company)
        return config

    @extend_schema(summary="Configuration des durées de caisses", responses={200: ConfigurationCaisseSerializer})
    def get(self, request):
        company = request.user.company
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)
        config = self._get_or_create_config(company)
        return Response(ConfigurationCaisseSerializer(config).data)

    @extend_schema(summary="Modifier la configuration des durées de caisses", responses={200: ConfigurationCaisseSerializer})
    def patch(self, request):
        company = request.user.company
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)
        config = self._get_or_create_config(company)
        s = ConfigurationCaisseSerializer(config, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save(updated_by=request.user)
        return Response(s.data)


# ── Taux de change ────────────────────────────────────────────────────────────

@extend_schema(tags=["Finance — Taux de change"])
class TauxChangeViewSet(CompanyFilterMixin, GenericViewSet,
                        ListModelMixin, RetrieveModelMixin):

    queryset = TauxChange.objects.order_by('-created_at')
    serializer_class = TauxChangeSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_WRITE)()]

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
    zone_lookup_field = 'depot__zone'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_WRITE)()]

    def create(self, request, *args, **kwargs):
        s = CaissePhysiqueSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Fermer définitivement une caisse physique",
        description=(
            "Fermeture irréversible. Impossible si une session est encore ouverte "
            "sur cette caisse (règle universelle §1 et §5)."
        ),
    )
    @action(detail=True, methods=['post'], url_path='fermer',
            permission_classes=[IsAuthenticated, HasAnyRole(Role.ADMIN)])
    def fermer(self, request, pk=None):
        caisse = self.get_object()
        if caisse.statut == CaissePhysique.Statut.FERMEE:
            raise ValidationError("Cette caisse est déjà fermée définitivement.")
        sessions_ouvertes = SessionCaisse.objects.filter(
            caisse=caisse, statut=SessionCaisse.Statut.OUVERTE
        ).exists()
        if sessions_ouvertes:
            raise ValidationError(
                "Impossible de fermer cette caisse : une session est encore ouverte."
            )
        caisse.statut = CaissePhysique.Statut.FERMEE
        from django.utils import timezone as tz
        caisse.fermee_le = tz.now()
        caisse.is_active = False
        caisse.save(update_fields=['statut', 'fermee_le', 'is_active'])
        return Response(CaissePhysiqueSerializer(caisse).data)


# ── Sessions caisse ───────────────────────────────────────────────────────────

@extend_schema(tags=["Finance — Sessions"])
class SessionCaisseViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    def get_permissions(self):
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]

    def get_serializer_class(self):
        return SessionCaisseListSerializer if self.action == 'list' else SessionCaisseDetailSerializer

    def get_queryset(self):
        qs = SessionCaisse.objects.select_related(
            'caisse__depot__zone', 'caissier', 'fermee_par'
        ).prefetch_related('transactions').order_by('-ouvert_le')

        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(caisse__company=company)

        if user.role == Role.SUPERVISEUR:
            if not user.zone:
                return qs.none()
            qs = qs.filter(caisse__depot__zone=user.zone)
        elif user.role == Role.CAISSIER:
            qs = qs.filter(caissier=user)

        caisse = self.request.query_params.get('caisse')
        statut = self.request.query_params.get('statut')
        if caisse:
            qs = qs.filter(caisse_id=caisse)
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    @extend_schema(summary="Ouvrir une session de caisse")
    @action(detail=False, methods=['post'], url_path='ouvrir',
            permission_classes=[IsAuthenticated, HasAnyRole(Role.CAISSIER, Role.ADMIN)])
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

        # Le superviseur ne peut ouvrir que dans sa zone
        user = request.user
        if user.role == Role.SUPERVISEUR:
            if not user.zone or caisse.depot.zone != user.zone:
                raise PermissionDenied("Vous ne pouvez intervenir que sur les caisses de votre zone.")

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
    @action(detail=True, methods=['post'], url_path='fermer',
            permission_classes=[IsAuthenticated, HasAnyRole(*FINANCE_READ)])
    def fermer(self, request, pk=None):
        session = self.get_object()
        user = request.user

        # Règle : seul le caissier de la session, l'admin, ou le superviseur de la même zone
        if user.role == Role.CAISSIER and session.caissier != user:
            raise PermissionDenied("Vous ne pouvez fermer que votre propre session de caisse.")
        if user.role == Role.SUPERVISEUR:
            if not user.zone:
                raise PermissionDenied("Votre compte superviseur n'est pas assigné à une zone.")
            if session.caisse.depot.zone != user.zone:
                raise PermissionDenied("Vous ne pouvez intervenir que sur les sessions de votre zone.")

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

        ecart = d['solde_reel'] - session.solde_fermeture_theorique
        if ecart != 0 and not d.get('motif_ecart'):
            raise ValidationError(
                {'motif_ecart': "Un motif est obligatoire lorsqu'il y a un écart de caisse."}
            )

        try:
            session.fermer(
                solde_reel=d['solde_reel'],
                motif_ecart=d.get('motif_ecart', ''),
                fermee_par=request.user,
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
    zone_lookup_field = 'depot__zone'

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'transactions'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_WRITE)()]

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
    zone_lookup_field = 'zone'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_WRITE)()]

    def create(self, request, *args, **kwargs):
        s = CaisseZoneSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Fermer définitivement une caisse zone",
        description=(
            "Fermeture irréversible. Impossible si une CaissePhysique de la zone "
            "est encore ouverte (règle universelle §5)."
        ),
    )
    @action(detail=True, methods=['post'], url_path='fermer',
            permission_classes=[IsAuthenticated, HasAnyRole(Role.ADMIN)])
    def fermer(self, request, pk=None):
        caisse_zone = self.get_object()
        if caisse_zone.statut == CaisseZone.Statut.FERMEE:
            raise ValidationError("Cette caisse zone est déjà fermée définitivement.")
        caisses_physiques_ouvertes = CaissePhysique.objects.filter(
            company=caisse_zone.company,
            depot__zone=caisse_zone.zone,
            statut=CaissePhysique.Statut.OUVERTE,
        ).exists()
        if caisses_physiques_ouvertes:
            raise ValidationError(
                "Impossible de fermer cette caisse zone : "
                "des caisses physiques de la zone sont encore ouvertes."
            )
        caisse_zone.statut = CaisseZone.Statut.FERMEE
        from django.utils import timezone as tz
        caisse_zone.fermee_le = tz.now()
        caisse_zone.is_active = False
        caisse_zone.save(update_fields=['statut', 'fermee_le', 'is_active'])
        return Response(CaisseZoneSerializer(caisse_zone).data)


# ── Caisse Entreprise ─────────────────────────────────────────────────────────
@extend_schema(tags=["Finance — Caisse Entreprise"])
class CaisseEntrepriseViewSet(GenericViewSet, RetrieveModelMixin):
    """Une seule caisse par entreprise — lecture seule via /caisse-entreprise/me/."""

    serializer_class = CaisseEntrepriseSerializer

    def get_permissions(self):
        # Configuration = admin uniquement ; lecture = rôles finance.
        if self.action == 'configurer':
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_WRITE)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]

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

    @extend_schema(summary="Configurer la caisse entreprise (admin)")
    @action(detail=False, methods=['patch'], url_path='configurer')
    def configurer(self, request):
        # Crée la caisse si elle n'existe pas encore (entreprises créées avant
        # l'auto-création), puis applique nom / devise.
        obj, _ = CaisseEntreprise.objects.get_or_create(
            company=request.user.company,
            defaults={
                'nom': f"Caisse {request.user.company.name}",
                'devise': 'GNF',
            },
        )
        serializer = CaisseEntrepriseSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ── Versements inter-niveaux ──────────────────────────────────────────────────
@extend_schema(tags=["Finance — Versements"])
class VersementCaisseViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = VersementCaisseSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_WRITE)()]

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
        if user.role == Role.SUPERVISEUR:
            if not user.zone:
                return qs.none()
            qs = qs.filter(
                models.Q(caisse_source_depot__depot__zone=user.zone) |
                models.Q(caisse_source_zone__zone=user.zone)
            )
        return qs

    def create(self, request, *args, **kwargs):
        s = VersementCaisseSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company

        # Vérifier que toutes les caisses appartiennent à la company de l'utilisateur
        src_depot = d.get('caisse_source_depot')
        src_zone = d.get('caisse_source_zone')
        dst_zone = d.get('caisse_dest_zone')
        dst_ent = d.get('caisse_dest_entreprise')
        caisses = [c for c in [src_depot, src_zone, dst_zone, dst_ent] if c is not None]
        for caisse in caisses:
            if caisse.company != company:
                raise ValidationError("Vous ne pouvez effectuer des versements qu'entre les caisses de votre entreprise.")

        # Règle universelle §1 : versement interdit depuis une caisse définitivement fermée
        if src_depot and src_depot.statut == CaissePhysique.Statut.FERMEE:
            raise ValidationError(
                "Impossible d'effectuer un versement depuis une caisse physique fermée définitivement."
            )
        if src_zone and src_zone.statut == CaisseZone.Statut.FERMEE:
            raise ValidationError(
                "Impossible d'effectuer un versement depuis une caisse zone fermée définitivement."
            )

        with transaction.atomic():
            versement = VersementCaisse.objects.create(
                effectue_par=request.user, **d)
            # Mettre à jour les soldes des caisses
            montant = d['montant']
            if d['type_versement'] == VersementCaisse.TypeVersement.DEPOT_VERS_ZONE:
                if src_depot:
                    src_depot.solde_actuel -= montant
                    src_depot.save(update_fields=['solde_actuel'])
                if dst_zone:
                    dst_zone.solde_actuel += montant
                    dst_zone.save(update_fields=['solde_actuel'])
            elif d['type_versement'] == VersementCaisse.TypeVersement.ZONE_VERS_ENTREPRISE:
                if src_zone:
                    src_zone.solde_actuel -= montant
                    src_zone.save(update_fields=['solde_actuel'])
                if dst_ent:
                    dst_ent.solde_actuel += montant
                    dst_ent.save(update_fields=['solde_actuel'])

        return Response(VersementCaisseSerializer(versement).data,
                        status=status.HTTP_201_CREATED)


# ── Dépenses opérationnelles ──────────────────────────────────────────────────
@extend_schema(tags=["Finance — Dépenses"])
class DepenseOperationnelleViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    serializer_class = DepenseOperationnelleSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_WRITE)()]

    def get_queryset(self):
        qs = DepenseOperationnelle.objects.select_related(
            'company', 'depot__zone', 'enregistre_par'
        ).filter(is_deleted=False).order_by('-date_depense')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(company=company)
        if user.role == Role.SUPERVISEUR:
            if not user.zone:
                return qs.none()
            qs = qs.filter(depot__zone=user.zone)
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
        from django.utils import timezone as tz
        obj = self.get_object()
        obj.is_deleted = True
        obj.deleted_at = tz.now()
        obj.save(update_fields=['is_deleted', 'deleted_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Vue consolidée tous niveaux ───────────────────────────────────────────────

@extend_schema(tags=["Finance — Consolidation"])
class ConsolidationCaissesView(APIView):
    """Vue consolidée des soldes de tous les niveaux de caisses."""

    def get_permissions(self):
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*FINANCE_READ)()]

    @extend_schema(summary="Soldes consolidés — tous niveaux de caisses", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        company = request.user.company
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)

        from django.db.models import Sum

        user = request.user
        caisses_depot = CaissePhysique.objects.filter(company=company)
        caisses_zone = CaisseZone.objects.filter(company=company)
        caisse_ent = CaisseEntreprise.objects.filter(company=company)

        if user.role == Role.SUPERVISEUR:
            if not user.zone:
                return Response({'detail': "Superviseur non assigné à une zone."}, status=403)
            caisses_depot = caisses_depot.filter(depot__zone=user.zone)
            caisses_zone = caisses_zone.filter(zone=user.zone)
            caisse_ent = CaisseEntreprise.objects.none()

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
