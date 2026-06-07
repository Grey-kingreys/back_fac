"""
apps/finance/tests/conftest.py
Fixtures spécifiques aux finances (caisses, sessions).
"""

from decimal import Decimal

import pytest

from apps.finance.models import CaissePhysique, SessionCaisse


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
