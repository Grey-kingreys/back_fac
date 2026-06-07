"""
apps/ventes/tests/test_clients.py
Tests API : Clients, Créances.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.ventes.models import Client


CLIENTS_URL = "/api/clients/"
CREANCES_URL = "/api/clients/creances/"


def client_url(pk):
    return f"/api/clients/{pk}/"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/clients/
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestClientList:

    def test_caissier_voit_clients(self, client_caissier_a, client_vente):
        res = client_caissier_a.get(CLIENTS_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [c["id"] for c in res.data["results"]]
        assert client_vente.id in ids

    def test_admin_voit_clients(self, client_admin_a, client_vente):
        res = client_admin_a.get(CLIENTS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(CLIENTS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(CLIENTS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_isolation_company(self, client_admin_a, company_b, client_vente):
        cli_b = Client.objects.create(
            company=company_b, code="CLI-B01", nom="Barry", telephone="621000001",
        )
        res = client_admin_a.get(CLIENTS_URL)
        ids = [c["id"] for c in res.data["results"]]
        assert client_vente.id in ids
        assert cli_b.id not in ids


@pytest.mark.django_db
class TestClientCreate:

    def test_caissier_cree_client(self, client_caissier_a, company_a):
        payload = {
            "code": "CLI-NEW",
            "nom": "Kouyaté",
            "prenom": "Ibrahima",
            "telephone": "628000001",
        }
        res = client_caissier_a.post(CLIENTS_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert Client.objects.filter(company=company_a, code="CLI-NEW").exists()

    def test_admin_cree_client(self, client_admin_a, company_a):
        payload = {"code": "CLI-ADM", "nom": "Bah", "telephone": "628111222"}
        res = client_admin_a.post(CLIENTS_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.post(CLIENTS_URL, {"code": "X", "nom": "Y"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_code_unique_par_company(self, client_caissier_a, client_vente):
        payload = {
            "code": client_vente.code,
            "nom": "Doublon",
            "telephone": "628999000",
        }
        res = client_caissier_a.post(CLIENTS_URL, payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestClientDetail:

    def test_caissier_voit_detail(self, client_caissier_a, client_vente):
        res = client_caissier_a.get(client_url(client_vente.id))
        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == client_vente.id

    def test_admin_refuse_client_autre_company(self, client_admin_a, company_b):
        cli_b = Client.objects.create(company=company_b, code="CLI-B02", nom="Test")
        res = client_admin_a.get(client_url(cli_b.id))
        assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestClientUpdate:

    def test_caissier_modifie_client(self, client_caissier_a, client_vente):
        res = client_caissier_a.patch(client_url(client_vente.id), {"prenom": "Fatoumata"})
        assert res.status_code == status.HTTP_200_OK
        client_vente.refresh_from_db()
        assert client_vente.prenom == "Fatoumata"

    def test_chauffeur_refuse(self, client_chauffeur_a, client_vente):
        res = client_chauffeur_a.patch(client_url(client_vente.id), {"prenom": "Hack"})
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/clients/creances/
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestClientCreances:

    def test_admin_voit_creances(self, client_admin_a, company_a):
        Client.objects.create(
            company=company_a, code="CLI-CR", nom="Créancier",
            solde_credit=Decimal("50000"),
        )
        res = client_admin_a.get(CREANCES_URL)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] >= 1

    def test_seulement_clients_avec_solde(self, client_admin_a, client_vente, company_a):
        """Client sans solde ne doit pas apparaître dans les créances."""
        Client.objects.create(
            company=company_a, code="CLI-ZERO", nom="Sans solde",
            solde_credit=Decimal("0"),
        )
        res = client_admin_a.get(CREANCES_URL)
        results = res.data.get("results", res.data)
        if isinstance(results, list):
            for item in results:
                assert Decimal(str(item["solde_credit"])) > Decimal("0")

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(CREANCES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN
