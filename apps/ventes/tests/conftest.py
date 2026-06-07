"""
apps/ventes/tests/conftest.py
Fixtures spécifiques aux ventes (clients, produits stockés, commandes).
"""

from decimal import Decimal

import pytest

from apps.produits.models import Categorie, Produit, Unite
from apps.stocks.services import entree_stock
from apps.ventes.models import Client, Commande, Paiement, ParametresFidelite
from apps.ventes.services import creer_commande


@pytest.fixture
def categorie_a(db, company_a):
    return Categorie.objects.create(
        company=company_a, name="Alimentation", tva_taux=Decimal("0"),
    )


@pytest.fixture
def unite_a(db, company_a):
    return Unite.objects.create(company=company_a, name="Unité", symbole="u")


@pytest.fixture
def produit_a(db, company_a, categorie_a, unite_a):
    return Produit.objects.create(
        company=company_a,
        categorie=categorie_a,
        unite=unite_a,
        reference="VENTE-001",
        nom="Huile Végétale 1L",
        prix_achat=Decimal("15000"),
        prix_vente=Decimal("20000"),
        tva_taux=Decimal("0"),
        seuil_alerte=Decimal("5"),
    )


@pytest.fixture
def produit_stocked(db, depot_a, produit_a, caissier_a):
    """Produit avec 100 unités en stock dans depot_a."""
    entree_stock(
        depot=depot_a,
        produit=produit_a,
        quantite=Decimal("100"),
        utilisateur=caissier_a,
    )
    return produit_a


@pytest.fixture
def client_vente(db, company_a):
    return Client.objects.create(
        company=company_a,
        code="CLI-T01",
        nom="Diallo",
        prenom="Mariama",
        telephone="622000001",
        points_fidelite=0,
    )


@pytest.fixture
def parametres_fidelite(db, company_a):
    return ParametresFidelite.objects.create(
        company=company_a,
        is_active=True,
        tranche_montant=Decimal("10000"),
        points_par_tranche=1,
        valeur_point_gnf=Decimal("1000"),
    )


@pytest.fixture
def commande_a(db, company_a, depot_a, caissier_a, produit_stocked, client_vente):
    return creer_commande(
        company=company_a,
        depot=depot_a,
        caissier=caissier_a,
        lignes_data=[{"produit": produit_stocked.pk, "quantite": 2}],
        client=client_vente,
        montant_paye=Decimal("40000"),
        mode_paiement_initial=Paiement.Mode.ESPECES,
    )
