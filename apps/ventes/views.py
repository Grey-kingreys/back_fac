"""
apps/ventes/views.py
Clients, Commandes, Paiements, Paramètres fidélité
"""

from decimal import Decimal

from django.db import transaction

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
from apps.accounts.permissions import (
    CompanyFilterMixin, HasAnyRole, HasRole, IsCompanyMember, IsSuperAdminBlocked,
    apply_geo_scope, assert_depot_in_scope,
)

from .models import (
    Client,
    Commande,
    Devis,
    HistoriquePoints,
    LigneDevis,
    LigneRetour,
    Paiement,
    ParametresFidelite,
    Promotion,
    RetourCommande,
)
from .serializers import (
    ClientDetailSerializer,
    ClientListSerializer,
    CommandeCreateSerializer,
    CommandeDetailSerializer,
    CommandeListSerializer,
    DevisCreateSerializer,
    DevisDetailSerializer,
    DevisListSerializer,
    HistoriquePointsSerializer,
    LigneRetourCreateSerializer,
    PaiementInputSerializer,
    ParametresFideliteSerializer,
    PromotionSerializer,
    RetourCommandeCreateSerializer,
    RetourCommandeSerializer,
)
from .services import creer_commande, enregistrer_paiement


def _check_company(request, view, obj):
    if not IsCompanyMember().has_object_permission(request, view, obj):
        raise PermissionDenied("Vous n'avez pas accès à cette ressource.")


class VenteWriteMixin:
    READ_ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.CAISSIER, Role.COMMERCIAL]
    WRITE_ROLES = [Role.ADMIN, Role.CAISSIER]

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.READ_ROLES)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.WRITE_ROLES)()]


# ── Paramètres fidélité ───────────────────────────────────────────────────────

@extend_schema(tags=["Ventes — Fidélité"])
class ParametresFideliteView(APIView):

    def get_permissions(self):
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(Role.ADMIN)()]

    @extend_schema(summary="Lire les paramètres fidélité de l'entreprise", responses={200: ParametresFideliteSerializer})
    def get(self, request):
        company = request.user.company
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)
        params, _ = ParametresFidelite.objects.get_or_create(company=company)
        return Response(ParametresFideliteSerializer(params).data)

    @extend_schema(summary="Mettre à jour les paramètres fidélité", request=ParametresFideliteSerializer, responses={200: ParametresFideliteSerializer})
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

    @extend_schema(summary="Clients avec créances (solde > 0)")
    @action(detail=False, methods=['get'], url_path='creances')
    def creances(self, request):
        """Liste des clients ayant un solde crédit > 0."""
        qs = self.get_queryset().filter(solde_credit__gt=0).order_by('-solde_credit')
        from django.db.models import Sum
        total_creances = qs.aggregate(total=Sum('solde_credit'))['total'] or 0
        data = ClientDetailSerializer(qs, many=True, context={'request': request}).data
        return Response({
            'total_creances': str(total_creances),
            'count': qs.count(),
            'clients': data,
        })


# ── Commandes ─────────────────────────────────────────────────────────────────

@extend_schema(tags=["Ventes — Commandes"])
class CommandeViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    # Commercial crée les commandes ; caissier encaisse au comptoir ; admin supervise
    VENTE_ROLES = [Role.ADMIN, Role.CAISSIER, Role.COMMERCIAL]

    def get_permissions(self):
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.VENTE_ROLES)()]

    def get_serializer_class(self):
        return CommandeListSerializer if self.action == 'list' else CommandeDetailSerializer

    def get_queryset(self):
        qs = Commande.objects.select_related(
            'company', 'depot', 'client', 'caissier'
        ).prefetch_related('lignes__produit', 'paiements').order_by('-created_at')

        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(company=company)
        # Isolation géographique : commercial/caissier limités à leur dépôt,
        # superviseur à sa zone, admin à toute l'entreprise.
        qs = apply_geo_scope(qs, user, depot_fields='depot')

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

        # Vérifie entreprise ET périmètre géographique (dépôt/zone) de l'utilisateur.
        assert_depot_in_scope(request.user, depot)

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

    @extend_schema(summary="Générer la facture PDF")
    @action(detail=True, methods=['get'], url_path='facture')
    def facture_pdf(self, request, pk=None):
        from io import BytesIO

        from django.http import HttpResponse

        import reportlab.lib.pagesizes as ps
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

        commande = self.get_object()
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=ps.A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"FACTURE — {commande.numero}", styles['Title']))
        elements.append(Paragraph(
            f"Date : {commande.created_at.strftime('%d/%m/%Y')}", styles['Normal']))
        client_nom = commande.client.nom_complet if commande.client else "Client anonyme"
        elements.append(Paragraph(f"Client : {client_nom}", styles['Normal']))
        elements.append(Paragraph(f"Dépôt : {commande.depot.code}", styles['Normal']))

        data = [["Produit", "Qté", "Prix HT", "TVA %", "Montant TTC"]]
        for ligne in commande.lignes.select_related('produit'):
            data.append([
                ligne.produit.nom,
                str(ligne.quantite),
                f"{ligne.prix_unitaire_ht} GNF",
                f"{ligne.tva_taux} %",
                f"{ligne.montant_ttc} GNF",
            ])
        data.append(["", "", "", "Total TTC :", f"{commande.montant_ttc} GNF"])
        data.append(["", "", "", "Remise :", f"{commande.remise} GNF"])
        data.append(["", "", "", "Payé :", f"{commande.montant_paye} GNF"])
        data.append(["", "", "", "Reste à payer :", f"{commande.reste_a_payer} GNF"])

        t = Table(data, colWidths=[180, 50, 90, 60, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(t)
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="facture-{commande.numero}.pdf"')
        return response

    @extend_schema(summary="Générer le bon de livraison PDF")
    @action(detail=True, methods=['get'], url_path='bon-livraison')
    def bon_livraison_pdf(self, request, pk=None):
        from io import BytesIO

        from django.http import HttpResponse

        import reportlab.lib.pagesizes as ps
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

        commande = self.get_object()
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=ps.A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"BON DE LIVRAISON — {commande.numero}", styles['Title']))
        elements.append(Paragraph(
            f"Date : {commande.created_at.strftime('%d/%m/%Y')}", styles['Normal']))
        client_nom = commande.client.nom_complet if commande.client else "Client anonyme"
        elements.append(Paragraph(f"Client : {client_nom}", styles['Normal']))

        data = [["Référence", "Produit", "Quantité", "Unité"]]
        for ligne in commande.lignes.select_related('produit__unite'):
            data.append([
                ligne.produit.reference,
                ligne.produit.nom,
                str(ligne.quantite),
                ligne.produit.unite.symbole if ligne.produit.unite else '',
            ])

        t = Table(data, colWidths=[80, 220, 70, 70])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(t)
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="bl-{commande.numero}.pdf"')
        return response


# ── Devis ─────────────────────────────────────────────────────────────────────

@extend_schema(tags=["Ventes — Devis"])
class DevisViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    DEVIS_READ_ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.COMMERCIAL, Role.CAISSIER]
    DEVIS_WRITE_ROLES = [Role.ADMIN, Role.COMMERCIAL, Role.CAISSIER]

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.DEVIS_READ_ROLES)()]
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.DEVIS_WRITE_ROLES)()]

    def get_serializer_class(self):
        return DevisListSerializer if self.action == 'list' else DevisDetailSerializer

    def get_queryset(self):
        qs = Devis.objects.select_related(
            'company', 'depot', 'client', 'cree_par'
        ).prefetch_related('lignes__produit').order_by('-created_at')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(company=company)
        qs = apply_geo_scope(qs, user, depot_fields='depot')
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    @extend_schema(summary="Créer un devis")
    def create(self, request, *args, **kwargs):
        s = DevisCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company
        if not company:
            raise ValidationError("Pas d'entreprise associée.")
        depot = d['depot']
        assert_depot_in_scope(request.user, depot)
        client = d.get('client')
        if client and client.company != company:
            raise ValidationError({'client': "Client introuvable."})

        with transaction.atomic():
            devis = Devis.objects.create(
                company=company,
                depot=depot,
                client=client,
                date_expiration=d.get('date_expiration'),
                notes=d.get('notes', ''),
                cree_par=request.user,
            )
            for ligne_data in d['lignes']:
                LigneDevis.objects.create(devis=devis, **ligne_data)

        return Response(
            DevisDetailSerializer(devis).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Convertir un devis en commande")
    @action(detail=True, methods=['post'], url_path='convertir')
    def convertir(self, request, pk=None):
        devis = self.get_object()
        if devis.statut == Devis.Statut.CONVERTI:
            raise ValidationError("Ce devis a déjà été converti.")
        if devis.statut == Devis.Statut.REFUSE:
            raise ValidationError("Impossible de convertir un devis refusé.")
        if devis.statut == Devis.Statut.EXPIRE:
            raise ValidationError("Impossible de convertir un devis expiré.")

        company = request.user.company or devis.company
        lignes_data = [
            {
                'produit': ligne.produit_id,
                'quantite': ligne.quantite,
                'prix_unitaire_ht': ligne.prix_unitaire_ht,
            }
            for ligne in devis.lignes.all()
        ]
        try:
            commande = creer_commande(
                company=company,
                depot=devis.depot,
                caissier=request.user,
                lignes_data=lignes_data,
                client=devis.client,
                mode_paiement=Commande.ModePaiement.CREDIT,
                remise=Decimal('0'),
                points_utilises=0,
                notes=f"Converti depuis devis {devis.numero}",
                montant_paye=Decimal('0'),
            )
        except (ValueError, Exception) as e:
            raise ValidationError(str(e))

        devis.statut = Devis.Statut.CONVERTI
        devis.commande = commande
        devis.save(update_fields=['statut', 'commande'])
        return Response(DevisDetailSerializer(devis).data)


# ── Retours commandes ─────────────────────────────────────────────────────────

@extend_schema(tags=["Ventes — Retours"])
class RetourCommandeViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    RETOUR_ROLES = [Role.ADMIN, Role.SUPERVISEUR, Role.CAISSIER]

    def get_permissions(self):
        return [IsAuthenticated(), IsSuperAdminBlocked(), HasAnyRole(*self.RETOUR_ROLES)()]

    def get_serializer_class(self):
        return RetourCommandeSerializer

    def get_queryset(self):
        qs = RetourCommande.objects.select_related(
            'commande__company', 'traite_par'
        ).prefetch_related('lignes__produit').order_by('-created_at')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(commande__company=company)
        qs = apply_geo_scope(qs, user, depot_fields='commande__depot')
        return qs

    @extend_schema(summary="Créer un retour commande")
    def create(self, request, *args, **kwargs):
        s = RetourCommandeCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        commande = d['commande']
        company = request.user.company
        if commande.company != company:
            raise PermissionDenied("Cette commande n'appartient pas à votre entreprise.")
        # Caissier limité aux commandes de son dépôt (superviseur : sa zone).
        assert_depot_in_scope(request.user, commande.depot)

        with transaction.atomic():
            from apps.stocks.services import entree_stock
            retour = RetourCommande.objects.create(
                commande=commande,
                motif=d['motif'],
                type_retour=d['type_retour'],
                montant_rembourse=d.get('montant_rembourse', Decimal('0')),
                notes=d.get('notes', ''),
                traite_par=request.user,
            )
            for ligne_data in d['lignes']:
                LigneRetour.objects.create(retour=retour, **ligne_data)
                entree_stock(
                    depot=commande.depot,
                    produit=ligne_data['produit'],
                    quantite=ligne_data['quantite'],
                    utilisateur=request.user,
                    motif=f"Retour commande {commande.numero}",
                    reference_doc=commande.numero,
                )

        return Response(
            RetourCommandeSerializer(retour).data, status=status.HTTP_201_CREATED)


# ── Historique points fidélité ────────────────────────────────────────────────

@extend_schema(tags=["Ventes — Fidélité"])
class HistoriquePointsViewSet(GenericViewSet, ListModelMixin):

    def get_permissions(self):
        return [IsAuthenticated(), IsSuperAdminBlocked(),
                HasAnyRole(Role.ADMIN, Role.SUPERVISEUR, Role.CAISSIER, Role.COMMERCIAL)()]

    def get_serializer_class(self):
        return HistoriquePointsSerializer

    def get_queryset(self):
        qs = HistoriquePoints.objects.select_related('client', 'commande').order_by('-created_at')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(client__company=company)
        client_id = self.request.query_params.get('client')
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs


# ── Promotions ────────────────────────────────────────────────────────────────
@extend_schema(tags=["Ventes — Promotions"])
class PromotionViewSet(VenteWriteMixin, CompanyFilterMixin, GenericViewSet,
                       ListModelMixin, RetrieveModelMixin):
    """CRUD promotions et remises commerciales."""
    serializer_class = PromotionSerializer
    queryset = Promotion.objects.order_by('-date_debut')
    # Les promotions sont créées/modifiées par l'admin uniquement (décision commerciale)
    WRITE_ROLES = [Role.ADMIN]

    def get_queryset(self):
        qs = super().get_queryset()
        active = self.request.query_params.get('active')
        if active is not None:
            from django.utils import timezone
            today = timezone.now().date()
            if active.lower() in ('true', '1'):
                qs = qs.filter(is_active=True, date_debut__lte=today, date_fin__gte=today)
            else:
                qs = qs.filter(is_active=False)
        return qs

    def create(self, request, *args, **kwargs):
        s = PromotionSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        company = request.user.company
        s.save(company=company, created_by=request.user)
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = PromotionSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': "Promotion désactivée."})
