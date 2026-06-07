"""
apps/stocks/tests/conftest.py
Fixtures spécifiques aux stocks.
"""

from decimal import Decimal

import pytest

from apps.produits.models import Categorie, Produit, Unite
from apps.stocks.models import StockDepot
from apps.stocks.services import entree_stock


@pytest.fixture
def categorie_a(db, company_a):
    return Categorie.objects.create(
        company=company_a, name="Alimentation", tva_taux=Decimal("0"),
    )


@pytest.fixture
def unite_a(db, company_a):
    return Unite.objects.create(company=company_a, name="Kilogramme", symbole="kg")


@pytest.fixture
def produit_a(db, company_a, categorie_a, unite_a):
    return Produit.objects.create(
        company=company_a,
        categorie=categorie_a,
        unite=unite_a,
        reference="PROD-S01",
        nom="Riz Parfumé",
        prix_achat=Decimal("80000"),
        prix_vente=Decimal("100000"),
        tva_taux=Decimal("0"),
        seuil_alerte=Decimal("10"),
    )


@pytest.fixture
def produit_b(db, company_a, categorie_a, unite_a):
    return Produit.objects.create(
        company=company_a,
        categorie=categorie_a,
        unite=unite_a,
        reference="PROD-S02",
        nom="Huile Végétale",
        prix_achat=Decimal("15000"),
        prix_vente=Decimal("20000"),
        tva_taux=Decimal("0"),
        seuil_alerte=Decimal("5"),
    )


@pytest.fixture
def stock_a(db, depot_a, produit_a, gestionnaire_a):
    """Stock approvisionné de 50 unités de produit_a dans depot_a."""
    entree_stock(
        depot=depot_a,
        produit=produit_a,
        quantite=Decimal("50"),
        utilisateur=gestionnaire_a,
    )
    return StockDepot.objects.get(depot=depot_a, produit=produit_a)
