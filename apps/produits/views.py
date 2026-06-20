"""
apps/produits/views.py
CRUD : Categorie, Unite, Fournisseur, Produit
"""

from django.db import transaction

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasAnyRole, HasRole, IsCompanyMember, IsSuperAdminBlocked

from .models import (
    Categorie,
    CommandeFournisseur,
    EvaluationFournisseur,
    Fournisseur,
    MouvementDetteFournisseur,
    Produit,
    Unite,
)
from .serializers import (
    CategorieSerializer,
    CommandeFournisseurCreateSerializer,
    CommandeFournisseurDetailSerializer,
    CommandeFournisseurListSerializer,
    EvaluationFournisseurSerializer,
    FournisseurDetailSerializer,
    FournisseurListSerializer,
    LigneCommandeFournisseurSerializer,
    MouvementDetteFournisseurSerializer,
    ProduitDetailSerializer,
    ProduitListSerializer,
    UniteSerializer,
)


class CompanyWriteMixin:
    """Permissions : lecture large, écriture admin+."""

    READ_ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK,
                  Role.COMMERCIAL, Role.CAISSIER]
    WRITE_ROLES = [Role.ADMIN]

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'stock'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.READ_ROLES)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.WRITE_ROLES)()]

    def _check_company(self, request, instance):
        if not IsCompanyMember().has_object_permission(request, self, instance):
            raise PermissionDenied("Vous n'avez pas accès à cette ressource.")


# ── Catégories ────────────────────────────────────────────────────────────────

@extend_schema(tags=["Produits — Catégories"])
class CategorieViewSet(CompanyWriteMixin, CompanyFilterMixin,
                       GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Categorie.objects.prefetch_related('produits').order_by('name')
    serializer_class = CategorieSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        v = self.request.query_params.get('is_active')
        if v is not None:
            qs = qs.filter(is_active=v.lower() in ('true', '1'))
        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        return Response(self.get_serializer(obj).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        s = self.get_serializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Catégorie '{obj.name}' désactivée."})


# ── Unités ────────────────────────────────────────────────────────────────────

@extend_schema(tags=["Produits — Unités"])
class UniteViewSet(CompanyWriteMixin, CompanyFilterMixin,
                   GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Unite.objects.order_by('name')
    serializer_class = UniteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        v = self.request.query_params.get('is_active')
        if v is not None:
            qs = qs.filter(is_active=v.lower() in ('true', '1'))
        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        return Response(self.get_serializer(obj).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        s = self.get_serializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Unité '{obj.name}' désactivée."})


# ── Fournisseurs ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Fournisseurs"])
class FournisseurViewSet(CompanyWriteMixin, CompanyFilterMixin,
                         GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Fournisseur.objects.order_by('nom')

    def get_serializer_class(self):
        return FournisseurListSerializer if self.action == 'list' else FournisseurDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        v = self.request.query_params.get('is_active')
        search = self.request.query_params.get('search')
        if v is not None:
            qs = qs.filter(is_active=v.lower() in ('true', '1'))
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(nom__icontains=search) | Q(code__icontains=search))
        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        return Response(FournisseurDetailSerializer(obj, context={'request': request}).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(
            FournisseurDetailSerializer(s.instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        s = self.get_serializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(FournisseurDetailSerializer(obj, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Fournisseur '{obj.nom}' désactivé."})

    @extend_schema(summary="Évaluations d'un fournisseur")
    @action(detail=True, methods=['get'], url_path='evaluations')
    def evaluations(self, request, pk=None):
        fournisseur = self.get_object()
        qs = EvaluationFournisseur.objects.filter(fournisseur=fournisseur).order_by('-created_at')
        return Response(EvaluationFournisseurSerializer(qs, many=True).data)


# ── Produits ──────────────────────────────────────────────────────────────────

@extend_schema(tags=["Produits"])
class ProduitViewSet(CompanyWriteMixin, CompanyFilterMixin,
                     GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Produit.objects.select_related(
        'categorie', 'unite', 'fournisseur_principal'
    ).order_by('nom')

    def get_serializer_class(self):
        return ProduitListSerializer if self.action == 'list' else ProduitDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        from django.db.models import Q
        v = self.request.query_params.get('is_active')
        cat = self.request.query_params.get('categorie')
        search = self.request.query_params.get('search')
        if v is not None:
            qs = qs.filter(is_active=v.lower() in ('true', '1'))
        if cat:
            qs = qs.filter(categorie_id=cat)
        if search:
            qs = qs.filter(
                Q(nom__icontains=search)
                | Q(reference__icontains=search)
                | Q(code_barre__icontains=search)
            )
        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        return Response(ProduitDetailSerializer(obj, context={'request': request}).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(
            ProduitDetailSerializer(s.instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        s = self.get_serializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(ProduitDetailSerializer(obj, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self._check_company(request, obj)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Produit '{obj.nom}' désactivé."})

    @extend_schema(summary="Stock par dépôt pour un produit")
    @action(detail=True, methods=['get'], url_path='stock')
    def stock(self, request, pk=None):
        from apps.stocks.models import StockDepot
        obj = self.get_object()
        self._check_company(request, obj)
        stocks = StockDepot.objects.filter(produit=obj).select_related('depot__zone')
        return Response({
            'produit_id': obj.pk,
            'stocks': [
                {
                    'depot_id': s.depot_id,
                    'depot_code': s.depot.code,
                    'depot_nom': s.depot.name,
                    'zone_nom': s.depot.zone.name,
                    'quantite': s.quantite,
                }
                for s in stocks
            ],
        })


# ── Commandes fournisseurs ────────────────────────────────────────────────────
@extend_schema(tags=["Fournisseurs — Commandes"])
class CommandeFournisseurViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK]
    WRITE_ROLES = [Role.ADMIN, Role.GESTIONNAIRE_STOCK]

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.ROLES)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.WRITE_ROLES)()]

    def get_serializer_class(self):
        if self.action == 'list':
            return CommandeFournisseurListSerializer
        return CommandeFournisseurDetailSerializer

    def get_queryset(self):
        qs = CommandeFournisseur.objects.select_related(
            'fournisseur', 'depot_destination', 'created_par'
        ).prefetch_related('lignes__produit').order_by('-created_at')
        user = self.request.user
        if not user.company:
            return qs.none()
        qs = qs.filter(company=user.company)
        statut = self.request.query_params.get('statut')
        fournisseur = self.request.query_params.get('fournisseur')
        if statut:
            qs = qs.filter(statut=statut)
        if fournisseur:
            qs = qs.filter(fournisseur_id=fournisseur)
        return qs

    def create(self, request, *args, **kwargs):
        s = CommandeFournisseurCreateSerializer(
            data=request.data, context={'request': request}
        )
        s.is_valid(raise_exception=True)
        commande = s.save()
        return Response(CommandeFournisseurDetailSerializer(commande).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(summary="Réceptionner une commande fournisseur → entrée stock")
    @action(detail=True, methods=['post'], url_path='recevoir')
    def recevoir(self, request, pk=None):
        from apps.stocks.services import entree_stock
        commande = self.get_object()
        if commande.statut == CommandeFournisseur.Statut.ANNULEE:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Impossible de réceptionner une commande annulée.")

        lignes_data = request.data.get('lignes', [])
        with transaction.atomic():
            total_commandees = 0
            total_recues = 0
            for item in lignes_data:
                ligne_id = item.get('ligne_id')
                qte_recue = item.get('quantite_recue', 0)
                try:
                    ligne = commande.lignes.get(pk=ligne_id)
                except Exception:
                    continue
                if qte_recue > 0:
                    entree_stock(
                        depot=commande.depot_destination,
                        produit=ligne.produit,
                        quantite=qte_recue,
                        utilisateur=request.user,
                        reference_doc=commande.numero,
                        motif=f"Réception commande fournisseur {commande.numero}",
                    )
                    ligne.quantite_recue += qte_recue
                    ligne.save(update_fields=['quantite_recue'])
                    # Mettre à jour la dette fournisseur
                    montant = ligne.prix_unitaire * qte_recue
                    MouvementDetteFournisseur.objects.create(
                        fournisseur=commande.fournisseur,
                        type_mouvement=MouvementDetteFournisseur.TypeMouvement.DETTE_AJOUTEE,
                        montant=montant,
                        reference=commande.numero,
                        created_par=request.user,
                    )
                    commande.fournisseur.solde_dette += montant
                    commande.fournisseur.save(update_fields=['solde_dette'])
                total_commandees += float(ligne.quantite_commandee)
                total_recues += float(ligne.quantite_recue)

            # Mettre à jour le statut
            if total_recues >= total_commandees:
                commande.statut = CommandeFournisseur.Statut.RECUE
            elif total_recues > 0:
                commande.statut = CommandeFournisseur.Statut.PARTIELLEMENT_RECUE
            commande.save(update_fields=['statut'])

        return Response(CommandeFournisseurDetailSerializer(commande).data)


# ── Mouvements dette fournisseur ──────────────────────────────────────────────
@extend_schema(tags=["Fournisseurs — Dettes"])
class MouvementDetteFournisseurViewSet(GenericViewSet, ListModelMixin):

    serializer_class = MouvementDetteFournisseurSerializer

    def get_permissions(self):
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(Role.ADMIN, Role.SUPERVISEUR)()]

    def get_queryset(self):
        qs = MouvementDetteFournisseur.objects.select_related(
            'fournisseur', 'created_par'
        ).order_by('-created_at')
        user = self.request.user
        if not user.company:
            return qs.none()
        qs = qs.filter(fournisseur__company=user.company)
        fournisseur = self.request.query_params.get('fournisseur')
        if fournisseur:
            qs = qs.filter(fournisseur_id=fournisseur)
        return qs

    def create(self, request, *args, **kwargs):
        s = MouvementDetteFournisseurSerializer(
            data=request.data, context={'request': request}
        )
        s.is_valid(raise_exception=True)
        # Isolation SaaS : le fournisseur doit appartenir à l'entreprise de l'utilisateur
        fournisseur = s.validated_data.get('fournisseur')
        if fournisseur is not None and fournisseur.company_id != request.user.company_id:
            raise ValidationError(
                "Ce fournisseur n'appartient pas à votre entreprise."
            )
        with transaction.atomic():
            mouvement = MouvementDetteFournisseur.objects.create(
                created_par=request.user, **s.validated_data)
            fournisseur = mouvement.fournisseur
            if mouvement.type_mouvement == MouvementDetteFournisseur.TypeMouvement.PAIEMENT_EFFECTUE:
                fournisseur.solde_dette -= mouvement.montant
            elif mouvement.type_mouvement == MouvementDetteFournisseur.TypeMouvement.DETTE_AJOUTEE:
                fournisseur.solde_dette += mouvement.montant
            fournisseur.save(update_fields=['solde_dette'])
        return Response(MouvementDetteFournisseurSerializer(mouvement).data,
                        status=status.HTTP_201_CREATED)


# ── Évaluations fournisseurs ──────────────────────────────────────────────────
@extend_schema(tags=["Produits — Évaluations fournisseurs"])
class EvaluationFournisseurViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    """CRUD évaluations fournisseurs."""
    serializer_class = EvaluationFournisseurSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(Role.ADMIN, Role.SUPERVISEUR)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(Role.ADMIN)()]

    def get_queryset(self):
        qs = EvaluationFournisseur.objects.select_related(
            'fournisseur', 'commande', 'evalue_par'
        ).order_by('-created_at')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(fournisseur__company=company)
        fournisseur_id = self.request.query_params.get('fournisseur')
        if fournisseur_id:
            qs = qs.filter(fournisseur_id=fournisseur_id)
        return qs

    def create(self, request, *args, **kwargs):
        s = EvaluationFournisseurSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save(evalue_par=request.user)
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = EvaluationFournisseurSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)
