"""
apps/finance/tests/conftest.py
Fixtures spécifiques aux finances (caisses, sessions).
"""

from decimal import Decimal

import pytest

from apps.finance.models import CaisseEntreprise, CaissePhysique, CaisseZone, SessionCaisse


@pytest.fixture
def caisse_a(db, company_a, depot_a):
    return CaissePhysique.objects.create(
        company=company_a,
        depot=depot_a,
        devise="GNF",
        solde_actuel=Decimal("500000"),
    )


@pytest.fixture
def session_a(db, caisse_a, caissier_a):
    return SessionCaisse.objects.create(
        caisse=caisse_a,
        caissier=caissier_a,
        solde_ouverture=Decimal("100000"),
        statut=SessionCaisse.Statut.OUVERTE,
    )


@pytest.fixture
def caisse_zone_a(db, company_a, zone_a):
    return CaisseZone.objects.create(
        company=company_a,
        zone=zone_a,
        devise="GNF",
        solde_actuel=Decimal("1000000"),
    )


@pytest.fixture
def caisse_entreprise_a(db, company_a):
    return CaisseEntreprise.objects.get_or_create(
        company=company_a,
        defaults={"devise": "GNF", "solde_actuel": Decimal("0")},
    )[0]
