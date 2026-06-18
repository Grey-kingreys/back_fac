"""
apps/stocks/tests/test_stocks.py
Tests API : StockDepot, Entrée stock, Sortie stock, Mouvements.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.stocks.models import MouvementStock, StockDepot


STOCKS_URL = "/api/stocks/"
ENTREE_URL = "/api/stocks/entree/"
SORTIE_URL = "/api/stocks/sortie/"
MOUVEMENTS_URL = "/api/mouvements-stock/"


def stock_url(pk):
    return f"/api/stocks/{pk}/"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/stocks/ — Liste stocks
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestStockList:

    def test_gestionnaire_voit_stocks_sa_company(self, client_gestionnaire_a, stock_a):
        res = client_gestionnaire_a.get(STOCKS_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [s["id"] for s in res.data["results"]]
        assert stock_a.id in ids

    def test_admin_voit_stocks(self, client_admin_a, stock_a):
        res = client_admin_a.get(STOCKS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_caissier_voit_stocks(self, client_caissier_a, stock_a):
        res = client_caissier_a.get(STOCKS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(STOCKS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(STOCKS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_isolation_depot_autre_company(self, client_admin_a, depot_b, produit_a):
        """Le stock d'un dépôt d'une autre company n'est pas visible."""
        res = client_admin_a.get(STOCKS_URL)
        for stock in res.data["results"]:
            assert stock["depot"] != depot_b.id

    def test_filtre_par_depot(self, client_gestionnaire_a, stock_a, depot_a):
        res = client_gestionnaire_a.get(STOCKS_URL, {"depot": depot_a.id})
        assert res.status_code == status.HTTP_200_OK
        for s in res.data["results"]:
            assert s["depot"] == depot_a.id

    def test_stock_en_alerte_flag(self, client_gestionnaire_a, stock_a, produit_a):
        """Stock sous le seuil d'alerte → en_alerte = True."""
        stock_a.quantite = Decimal("5")
        stock_a.save(update_fields=["quantite"])
        res = client_gestionnaire_a.get(stock_url(stock_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res.data["en_alerte"] is True


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/stocks/entree/ — Entrée stock
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEntreeStock:

    def test_gestionnaire_fait_entree(self, client_gestionnaire_a, produit_a, depot_a):
        payload = {
            "depot": depot_a.id,
            "produit": produit_a.id,
            "quantite": "20",
        }
        res = client_gestionnaire_a.post(ENTREE_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert StockDepot.objects.filter(depot=depot_a, produit=produit_a).exists()
        stock = StockDepot.objects.get(depot=depot_a, produit=produit_a)
        assert stock.quantite == Decimal("20")

    def test_entree_additive_si_stock_existe(self, client_gestionnaire_a, stock_a, produit_a, depot_a):
        qte_avant = stock_a.quantite
        payload = {"depot": depot_a.id, "produit": produit_a.id, "quantite": "10"}
        res = client_gestionnaire_a.post(ENTREE_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        stock_a.refresh_from_db()
        assert stock_a.quantite == qte_avant + Decimal("10")

    def test_entree_cree_mouvement(self, client_gestionnaire_a, produit_a, depot_a):
        payload = {"depot": depot_a.id, "produit": produit_a.id, "quantite": "15"}
        client_gestionnaire_a.post(ENTREE_URL, payload)
        assert MouvementStock.objects.filter(
            produit=produit_a,
            type_mouvement=MouvementStock.TypeMouvement.ENTREE,
        ).exists()

    def test_chauffeur_refuse_entree(self, client_chauffeur_a, produit_a, depot_a):
        payload = {"depot": depot_a.id, "produit": produit_a.id, "quantite": "5"}
        res = client_chauffeur_a.post(ENTREE_URL, payload)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_quantite_negative_refuse(self, client_gestionnaire_a, produit_a, depot_a):
        payload = {"depot": depot_a.id, "produit": produit_a.id, "quantite": "-5"}
        res = client_gestionnaire_a.post(ENTREE_URL, payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_anonyme_refuse(self, anon_client, produit_a, depot_a):
        res = anon_client.post(ENTREE_URL, {"depot": depot_a.id, "produit": produit_a.id, "quantite": "5"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/stocks/sortie/ — Sortie stock
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSortieStock:

    def test_gestionnaire_fait_sortie(self, client_gestionnaire_a, stock_a, produit_a, depot_a):
        payload = {"depot": depot_a.id, "produit": produit_a.id, "quantite": "10"}
        res = client_gestionnaire_a.post(SORTIE_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        stock_a.refresh_from_db()
        assert stock_a.quantite == Decimal("40")

    def test_sortie_insuffisant_refuse(self, client_gestionnaire_a, stock_a, produit_a, depot_a):
        payload = {"depot": depot_a.id, "produit": produit_a.id, "quantite": "9999"}
        res = client_gestionnaire_a.post(SORTIE_URL, payload)
        assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT)

    def test_caissier_peut_faire_sortie(self, client_caissier_a, stock_a, produit_a, depot_a):
        payload = {"depot": depot_a.id, "produit": produit_a.id, "quantite": "5"}
        res = client_caissier_a.post(SORTIE_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED

    def test_chauffeur_refuse_sortie(self, client_chauffeur_a, stock_a, produit_a, depot_a):
        payload = {"depot": depot_a.id, "produit": produit_a.id, "quantite": "5"}
        res = client_chauffeur_a.post(SORTIE_URL, payload)
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/mouvements-stock/ — Historique
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestMouvementStockList:

    def test_gestionnaire_voit_mouvements(self, client_gestionnaire_a, stock_a):
        res = client_gestionnaire_a.get(MOUVEMENTS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_admin_voit_mouvements(self, client_admin_a, stock_a):
        res = client_admin_a.get(MOUVEMENTS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(MOUVEMENTS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Règles universelles — Isolation dépôt pour le gestionnaire (M2)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestIsolationDepotGestionnaire:
    """Vérifie qu'un gestionnaire ne peut agir que sur son propre dépôt."""

    def test_gestionnaire_refuse_entree_autre_depot(
        self, client_gestionnaire_a, produit_a, depot_a2
    ):
        """Le gestionnaire_a est affecté à depot_a → il ne peut pas faire une entrée sur depot_a2."""
        payload = {
            "depot": depot_a2.id,
            "produit": produit_a.id,
            "quantite": "10",
        }
        res = client_gestionnaire_a.post(ENTREE_URL, payload)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_gestionnaire_accepte_entree_son_depot(
        self, client_gestionnaire_a, produit_a, depot_a
    ):
        """Le gestionnaire_a peut faire une entrée sur son propre dépôt."""
        payload = {
            "depot": depot_a.id,
            "produit": produit_a.id,
            "quantite": "10",
        }
        res = client_gestionnaire_a.post(ENTREE_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED


# ─────────────────────────────────────────────────────────────────────────────
# Règles universelles — Ajustements de stock (maker-checker §9 — séparation tâches)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAjustementMakerChecker:
    """Vérifie que le demandeur d'un ajustement ne peut pas l'approuver lui-même."""

    def _creer_ajustement(self, client, produit_a, depot_a):
        payload = {
            "depot": depot_a.id,
            "produit": produit_a.id,
            "quantite": "5",
            "motif": "Correction inventaire",
        }
        res = client.post("/api/ajustements-stock/", payload)
        assert res.status_code == status.HTTP_201_CREATED
        return res.data["id"]

    def test_gestionnaire_ne_peut_approuver_son_propre_ajustement(
        self, client_gestionnaire_a, client_admin_a, produit_a, depot_a, stock_a
    ):
        """Le gestionnaire qui a demandé l'ajustement ne peut pas l'approuver (maker-checker)."""
        ajustement_id = self._creer_ajustement(client_gestionnaire_a, produit_a, depot_a)
        # Le gestionnaire tente d'approuver → doit être refusé
        # (le gestionnaire n'a pas le rôle admin/superviseur, donc 403 rôle)
        res = client_gestionnaire_a.post(f"/api/ajustements-stock/{ajustement_id}/approuver/")
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_ne_peut_approuver_son_propre_ajustement(
        self, client_admin_a, produit_a, depot_a, stock_a
    ):
        """Un admin qui a lui-même créé l'ajustement ne peut pas l'approuver."""
        ajustement_id = self._creer_ajustement(client_admin_a, produit_a, depot_a)
        res = client_admin_a.post(f"/api/ajustements-stock/{ajustement_id}/approuver/")
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_superviseur_peut_approuver_ajustement_gestionnaire(
        self, client_gestionnaire_a, client_superviseur_a, produit_a, depot_a, stock_a
    ):
        """Le superviseur peut approuver un ajustement créé par le gestionnaire."""
        ajustement_id = self._creer_ajustement(client_gestionnaire_a, produit_a, depot_a)
        res = client_superviseur_a.post(f"/api/ajustements-stock/{ajustement_id}/approuver/")
        assert res.status_code == status.HTTP_200_OK
