"""
apps/companies/views_analytics.py
Endpoints analytiques — KPIs, CA, stocks, finance, TVA, performance.
"""

from decimal import Decimal

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import HasRole


ANALYTICS_ROLES = [Role.ADMIN, Role.SUPERVISEUR]


def _get_company(request):
    return request.user.company


def _parse_dates(request):
    from django.utils.dateparse import parse_date
    debut = request.query_params.get('debut')
    fin = request.query_params.get('fin')
    today = timezone.now().date()
    date_debut = parse_date(debut) if debut else today.replace(day=1)
    date_fin = parse_date(fin) if fin else today
    return date_debut, date_fin


@extend_schema(tags=["Analytics"])
class AnalyticsVentesView(APIView):

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(ANALYTICS_ROLES)]

    @extend_schema(summary="CA par période, par dépôt/zone", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from django.db.models import Count, Sum

        from apps.ventes.models import Commande

        company = _get_company(request)
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)

        date_debut, date_fin = _parse_dates(request)
        depot_id = request.query_params.get('depot')

        qs = Commande.objects.filter(
            company=company,
            created_at__date__gte=date_debut,
            created_at__date__lte=date_fin,
        ).exclude(statut='annulee')

        if depot_id:
            qs = qs.filter(depot_id=depot_id)

        totaux = qs.aggregate(
            nb_commandes=Count('id'),
            ca_ht=Sum('montant_ht'),
            ca_ttc=Sum('montant_ttc'),
            tva_total=Sum('tva_total'),
            montant_paye=Sum('montant_paye'),
        )

        par_depot = list(
            qs.values('depot__code', 'depot__name')
            .annotate(nb=Count('id'), ca_ttc=Sum('montant_ttc'))
            .order_by('-ca_ttc')
        )

        return Response({
            'periode': {'debut': str(date_debut), 'fin': str(date_fin)},
            'totaux': {k: str(v or Decimal('0')) for k, v in totaux.items()
                       if k != 'nb_commandes'} | {'nb_commandes': totaux['nb_commandes'] or 0},
            'par_depot': [
                {'depot_code': d['depot__code'], 'depot_nom': d['depot__name'],
                 'nb_commandes': d['nb'], 'ca_ttc': str(d['ca_ttc'] or Decimal('0'))}
                for d in par_depot
            ],
        })


@extend_schema(tags=["Analytics"])
class AnalyticsStockView(APIView):

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(ANALYTICS_ROLES)]

    @extend_schema(summary="Rotation stocks, produits en alerte, top produits", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from django.db.models import Count, Sum

        from apps.stocks.models import MouvementStock, StockDepot

        company = _get_company(request)
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)

        date_debut, date_fin = _parse_dates(request)

        stocks = StockDepot.objects.filter(
            depot__zone__company=company
        ).select_related('produit', 'depot')

        en_alerte = [
            {
                'produit_reference': s.produit.reference,
                'produit_nom': s.produit.nom,
                'depot_code': s.depot.code,
                'quantite': str(s.quantite),
                'seuil': str(s.produit.seuil_alerte),
            }
            for s in stocks if s.en_alerte
        ]

        top_sorties = list(
            MouvementStock.objects.filter(
                depot__zone__company=company,
                type_mouvement='sortie',
                created_at__date__gte=date_debut,
                created_at__date__lte=date_fin,
            ).values('produit__reference', 'produit__nom')
            .annotate(total_sortie=Sum('quantite'))
            .order_by('-total_sortie')[:10]
        )

        return Response({
            'periode': {'debut': str(date_debut), 'fin': str(date_fin)},
            'nb_produits_en_alerte': len(en_alerte),
            'produits_en_alerte': en_alerte,
            'top_produits_sortie': [
                {'reference': t['produit__reference'], 'nom': t['produit__nom'],
                 'total_sortie': str(t['total_sortie'] or Decimal('0'))}
                for t in top_sorties
            ],
        })


@extend_schema(tags=["Analytics"])
class AnalyticsFinanceView(APIView):

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(ANALYTICS_ROLES)]

    @extend_schema(summary="Recettes/dépenses, créances clients", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from django.db.models import Sum

        from apps.finance.models import TransactionCaisse
        from apps.ventes.models import Client

        company = _get_company(request)
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)

        date_debut, date_fin = _parse_dates(request)

        tx = TransactionCaisse.objects.filter(
            caisse__company=company,
            created_at__date__gte=date_debut,
            created_at__date__lte=date_fin,
        )
        entrees = tx.filter(type_transaction__in=['entree', 'vente']).aggregate(
            t=Sum('montant'))['t'] or Decimal('0')
        sorties = tx.filter(type_transaction__in=['sortie', 'remboursement']).aggregate(
            t=Sum('montant'))['t'] or Decimal('0')

        creances = Client.objects.filter(
            company=company, solde_credit__gt=0
        ).aggregate(total=Sum('solde_credit'))['total'] or Decimal('0')

        nb_clients_en_retard = Client.objects.filter(
            company=company, solde_credit__gt=0
        ).count()

        return Response({
            'periode': {'debut': str(date_debut), 'fin': str(date_fin)},
            'recettes': str(entrees),
            'depenses': str(sorties),
            'solde': str(entrees - sorties),
            'creances_clients': str(creances),
            'nb_clients_en_retard': nb_clients_en_retard,
        })


@extend_schema(tags=["Analytics"])
class AnalyticsTvaView(APIView):

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(ANALYTICS_ROLES)]

    @extend_schema(summary="TVA collectée par période", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from django.db.models import Sum

        from apps.ventes.models import Commande

        company = _get_company(request)
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)

        date_debut, date_fin = _parse_dates(request)

        result = Commande.objects.filter(
            company=company,
            created_at__date__gte=date_debut,
            created_at__date__lte=date_fin,
        ).exclude(statut='annulee').aggregate(
            tva_total=Sum('tva_total'),
            ca_ht=Sum('montant_ht'),
            ca_ttc=Sum('montant_ttc'),
        )

        return Response({
            'periode': {'debut': str(date_debut), 'fin': str(date_fin)},
            'tva_collectee': str(result['tva_total'] or Decimal('0')),
            'ca_ht': str(result['ca_ht'] or Decimal('0')),
            'ca_ttc': str(result['ca_ttc'] or Decimal('0')),
        })


@extend_schema(tags=["Analytics"])
class AnalyticsPerformanceView(APIView):

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(ANALYTICS_ROLES)]

    @extend_schema(summary="Objectifs vs réalisé par dépôt", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from apps.rh.models import ObjectifVente

        company = _get_company(request)
        if not company:
            return Response({'detail': "Pas d'entreprise associée."}, status=400)

        now = timezone.now()
        annee = int(request.query_params.get('annee', now.year))
        mois = int(request.query_params.get('mois', now.month))

        objectifs = ObjectifVente.objects.filter(
            company=company, annee=annee, mois=mois,
        ).select_related('depot')

        return Response({
            'annee': annee,
            'mois': mois,
            'depots': [
                {
                    'depot_code': o.depot.code,
                    'depot_nom': o.depot.name,
                    'objectif': str(o.montant_objectif),
                    'realise': str(o.montant_realise),
                    'taux_realisation': o.taux_realisation,
                }
                for o in objectifs
            ],
        })


# ── Dashboard SuperAdmin agrégé (toutes companies) ───────────────────────────
@extend_schema(tags=["Analytics — SuperAdmin"])
class SuperAdminDashboardView(APIView):
    """Tableau de bord global agrégé pour le SuperAdmin (toutes companies)."""

    def get_permissions(self):
        from apps.accounts.models import Role
        from apps.accounts.permissions import HasRole
        return [IsAuthenticated(), HasRole([Role.SUPERADMIN])]

    @extend_schema(summary="Tableau de bord global — toutes companies", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from django.db.models import Count, Sum
        from django.utils import timezone

        from apps.companies.models import Company
        today = timezone.now().date()

        # Résumé companies
        companies = Company.objects.annotate(
            nb_users=Count('users', distinct=True),
            nb_depots=Count('zones__depots', distinct=True),
        ).order_by('name')

        companies_data = []
        for c in companies:
            companies_data.append({
                'id': c.pk,
                'name': c.name,
                'plan': c.subscription_plan,
                'is_active': c.is_active,
                'nb_users': c.nb_users,
                'nb_depots': c.nb_depots,
            })

        # Totaux globaux
        total_companies = companies.count()
        total_actives = companies.filter(is_active=True).count()

        # Ventes du jour — toutes companies
        ventes_du_jour = {'count': 0, 'montant_ttc': 0}
        try:
            from apps.ventes.models import Commande
            agg = Commande.objects.filter(
                created_at__date=today,
                statut__in=['confirmee', 'livree'],
            ).aggregate(count=Count('id'), total=Sum('montant_ttc'))
            ventes_du_jour = {
                'count': agg['count'] or 0,
                'montant_ttc': str(agg['total'] or 0),
            }
        except Exception:
            pass

        # Stocks en alerte — toutes companies
        nb_alertes_stock = 0
        try:
            from apps.stocks.models import StockDepot
            for sd in StockDepot.objects.select_related('produit').all():
                if sd.en_alerte:
                    nb_alertes_stock += 1
        except Exception:
            pass

        # Missions actives — toutes companies
        nb_missions_actives = 0
        try:
            from apps.logistique.models import Mission
            nb_missions_actives = Mission.objects.filter(
                statut__in=['planifiee', 'chargement', 'en_transit']
            ).count()
        except Exception:
            pass

        # Utilisateurs actifs — toutes companies
        nb_users_total = 0
        try:
            from apps.accounts.models import User
            nb_users_total = User.objects.filter(is_active=True).count()
        except Exception:
            pass

        return Response({
            'companies': {
                'total': total_companies,
                'actives': total_actives,
                'suspendues': total_companies - total_actives,
                'detail': companies_data,
            },
            'utilisateurs_actifs': nb_users_total,
            'ventes_du_jour': ventes_du_jour,
            'alertes_stock': nb_alertes_stock,
            'missions_actives': nb_missions_actives,
        })
