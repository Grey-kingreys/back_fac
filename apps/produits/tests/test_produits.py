"""
apps/produits/tests/test_produits.py
Tests API : Catégories, Unités, Produits.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.produits.models import Categorie, Produit, Unite


CATEGORIES_URL = "/api/categories/"
UNITES_URL = "/api/unites/"
PRODUITS_URL = "/api/produits/"


def categorie_url(pk):
    return f"/api/categories/{pk}/"


def produit_url(pk):
    return f"/api/produits/{pk}/"


def produit_stock_url(pk):
    return f"/api/produits/{pk}/stock/"


# ─────────────────────────────────────────────────────────────────────────────
# Catégories
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCategorieList:

    def test_admin_voit_categories_sa_company(self, client_admin_a, categorie_a):
        res = client_admin_a.get(CATEGORIES_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [c["id"] for c in res.data["results"]]
        assert categorie_a.id in ids

    def test_isolation_company(self, client_admin_a, company_b):
        cat_b = Categorie.objects.create(company=company_b, name="Autre", tva_taux=Decimal("0"))
        res = client_admin_a.get(CATEGORIES_URL)
        ids = [c["id"] for c in res.data["results"]]
        assert cat_b.id not in ids

    def test_gestionnaire_peut_lister(self, client_gestionnaire_a, categorie_a):
        res = client_gestionnaire_a.get(CATEGORIES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(CATEGORIES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(CATEGORIES_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCategorieCreate:

    def test_admin_cree_categorie(self, client_admin_a, company_a):
        res = client_admin_a.post(CATEGORIES_URL, {"name": "Céréales", "tva_taux": "0"})
        assert res.status_code == status.HTTP_201_CREATED
        assert Categorie.objects.filter(company=company_a, name="Céréales").exists()

    def test_superviseur_refuse_creation(self, client_superviseur_a):
        res = client_superviseur_a.post(CATEGORIES_URL, {"name": "Test"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_company_injectee_automatiquement(self, client_admin_a, company_a):
        res = client_admin_a.post(CATEGORIES_URL, {"name": "Auto", "tva_taux": "0"})
        assert res.status_code == status.HTTP_201_CREATED
        cat = Categorie.objects.get(id=res.data["id"])
        assert cat.company == company_a


@pytest.mark.django_db
class TestCategorieUpdate:

    def test_admin_modifie_categorie(self, client_admin_a, categorie_a):
        res = client_admin_a.patch(categorie_url(categorie_a.id), {"name": "Alim. Modifiée"})
        assert res.status_code == status.HTTP_200_OK
        categorie_a.refresh_from_db()
        assert categorie_a.name == "Alim. Modifiée"

    def test_admin_refuse_categorie_autre_company(self, client_admin_a, company_b):
        cat_b = Categorie.objects.create(company=company_b, name="B Cat", tva_taux=Decimal("0"))
        res = client_admin_a.patch(categorie_url(cat_b.id), {"name": "Hack"})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_superviseur_refuse(self, client_superviseur_a, categorie_a):
        res = client_superviseur_a.patch(categorie_url(categorie_a.id), {"name": "X"})
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Unités
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUniteList:

    def test_admin_voit_unites(self, client_admin_a, unite_a):
        res = client_admin_a.get(UNITES_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [u["id"] for u in res.data["results"]]
        assert unite_a.id in ids

    def test_isolation_company(self, client_admin_a, company_b):
        u_b = Unite.objects.create(company=company_b, name="Litre", symbole="L")
        res = client_admin_a.get(UNITES_URL)
        ids = [u["id"] for u in res.data["results"]]
        assert u_b.id not in ids


@pytest.mark.django_db
class TestUniteCreate:

    def test_admin_cree_unite(self, client_admin_a, company_a):
        res = client_admin_a.post(UNITES_URL, {"name": "Tonne", "symbole": "T"})
        assert res.status_code == status.HTTP_201_CREATED
        assert Unite.objects.filter(company=company_a, symbole="T").exists()

    def test_superviseur_refuse(self, client_superviseur_a):
        res = client_superviseur_a.post(UNITES_URL, {"name": "Test", "symbole": "t"})
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Produits
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProduitList:

    def test_admin_voit_produits_sa_company(self, client_admin_a, produit_a):
        res = client_admin_a.get(PRODUITS_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in res.data["results"]]
        assert produit_a.id in ids

    def test_caissier_peut_lister(self, client_caissier_a, produit_a):
        res = client_caissier_a.get(PRODUITS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(PRODUITS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(PRODUITS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_superadmin_voit_tous_produits(self, client_superadmin, produit_a):
        res = client_superadmin.get(PRODUITS_URL)
        assert res.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestProduitCreate:

    def test_admin_cree_produit(self, client_admin_a, categorie_a, unite_a, company_a):
        payload = {
            "reference": "PROD-NEW",
            "nom": "Huile de Palme",
            "categorie": categorie_a.id,
            "unite": unite_a.id,
            "prix_achat": "25000",
            "prix_vente": "35000",
            "tva_taux": "0",
            "seuil_alerte": "5",
        }
        res = client_admin_a.post(PRODUITS_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert Produit.objects.filter(company=company_a, reference="PROD-NEW").exists()

    def test_superviseur_refuse_creation(self, client_superviseur_a):
        res = client_superviseur_a.post(PRODUITS_URL, {"nom": "X"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_reference_unique_par_company(self, client_admin_a, produit_a):
        payload = {
            "reference": produit_a.reference,
            "nom": "Doublon",
            "categorie": produit_a.categorie_id,
            "unite": produit_a.unite_id,
            "prix_achat": "1000",
            "prix_vente": "2000",
        }
        res = client_admin_a.post(PRODUITS_URL, payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestProduitDetail:

    def test_admin_voit_detail(self, client_admin_a, produit_a):
        res = client_admin_a.get(produit_url(produit_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == produit_a.id
        assert res.data["reference"] == produit_a.reference

    def test_admin_refuse_produit_autre_company(self, client_admin_a, company_b):
        cat = Categorie.objects.create(company=company_b, name="Cat B", tva_taux=Decimal("0"))
        u = Unite.objects.create(company=company_b, name="u", symbole="u")
        p = Produit.objects.create(
            company=company_b, categorie=cat, unite=u,
            reference="B001", nom="ProdB",
            prix_achat=Decimal("1000"), prix_vente=Decimal("2000"),
            tva_taux=Decimal("0"), seuil_alerte=Decimal("1"),
        )
        res = client_admin_a.get(produit_url(p.id))
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_404_produit_inexistant(self, client_admin_a):
        res = client_admin_a.get(produit_url(99999))
        assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestProduitStock:

    def test_stock_endpoint_retourne_donnees(self, client_gestionnaire_a, produit_a, depot_a):
        from apps.stocks.models import StockDepot
        StockDepot.objects.create(depot=depot_a, produit=produit_a, quantite=Decimal("50"))
        res = client_gestionnaire_a.get(produit_stock_url(produit_a.id))
        assert res.status_code == status.HTTP_200_OK

    def test_stock_endpoint_accessible_caissier(self, client_caissier_a, produit_a):
        res = client_caissier_a.get(produit_stock_url(produit_a.id))
        assert res.status_code == status.HTTP_200_OK
