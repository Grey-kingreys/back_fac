"""
apps/produits/tests/conftest.py
Fixtures spécifiques aux produits (catégories, unités, fournisseurs, produits).
"""

from decimal import Decimal

import pytest

from apps.produits.models import Categorie, Fournisseur, Produit, Unite


@pytest.fixture
def categorie_a(db, company_a):
    return Categorie.objects.create(
        company=company_a, name="Alimentation", tva_taux=Decimal("0"),
    )


@pytest.fixture
def unite_a(db, company_a):
    return Unite.objects.create(company=company_a, name="Kilogramme", symbole="kg")


@pytest.fixture
def fournisseur_a(db, company_a):
    return Fournisseur.objects.create(
        company=company_a,
        code="FRN-001",
        nom="Fournisseur Alpha",
        telephone="620000001",
    )


@pytest.fixture
def fournisseur_b(db, company_b):
    return Fournisseur.objects.create(
        company=company_b,
        code="FRN-002",
        nom="Fournisseur Beta",
    )


@pytest.fixture
def produit_a(db, company_a, categorie_a, unite_a):
    return Produit.objects.create(
        company=company_a,
        categorie=categorie_a,
        unite=unite_a,
        reference="PROD-001",
        nom="Riz Parfumé 25kg",
        prix_achat=Decimal("80000"),
        prix_vente=Decimal("100000"),
        tva_taux=Decimal("0"),
        seuil_alerte=Decimal("10"),
    )


@pytest.fixture
def produit_b(db, company_b):
    cat_b = Categorie.objects.create(company=company_b, name="Boissons", tva_taux=Decimal("0"))
    unite_b = Unite.objects.create(company=company_b, name="Litre", symbole="L")
    return Produit.objects.create(
        company=company_b,
        categorie=cat_b,
        unite=unite_b,
        reference="PROD-B01",
        nom="Eau Minérale 1.5L",
        prix_achat=Decimal("3000"),
        prix_vente=Decimal("5000"),
        tva_taux=Decimal("0"),
        seuil_alerte=Decimal("5"),
    )
