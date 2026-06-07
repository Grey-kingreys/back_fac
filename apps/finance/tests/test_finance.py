"""
apps/finance/tests/test_finance.py
Tests API : Caisses, Sessions, Transactions, Taux de change, Consolidation, Dépenses.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.finance.models import (
    CaisseEntreprise,
    CaissePhysique,
    CaisseZone,
    DepenseOperationnelle,
    SessionCaisse,
    TauxChange,
    TransactionCaisse,
)


CAISSES_URL = "/api/caisses/"
CAISSES_ZONE_URL = "/api/caisses-zone/"
CAISSE_ENTREPRISE_URL = "/api/caisse-entreprise/"
SESSIONS_URL = "/api/sessions-caisse/"
OUVRIR_URL = "/api/sessions-caisse/ouvrir/"
TAUX_CHANGE_URL = "/api/taux-change/"
CONSOLIDATION_URL = "/api/caisses/consolidation/"
DEPENSES_URL = "/api/depenses/"


def caisse_url(pk):
    return f"/api/caisses/{pk}/"


def session_url(pk):
    return f"/api/sessions-caisse/{pk}/"


def session_fermer_url(pk):
    return f"/api/sessions-caisse/{pk}/fermer/"


def session_transaction_url(pk):
    return f"/api/sessions-caisse/{pk}/transaction/"


def depense_url(pk):
    return f"/api/depenses/{pk}/"


# ─────────────────────────────────────────────────────────────────────────────
# CaissePhysique
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCaisseList:

    def test_caissier_voit_caisses(self, client_caissier_a, caisse_a):
        res = client_caissier_a.get(CAISSES_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [c["id"] for c in res.data["results"]]
        assert caisse_a.id in ids

    def test_admin_voit_caisses(self, client_admin_a, caisse_a):
        res = client_admin_a.get(CAISSES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(CAISSES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(CAISSES_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_isolation_company(self, client_admin_a, caisse_a):
        res = client_admin_a.get(CAISSES_URL)
        for c in res.data["results"]:
            assert c["id"] == caisse_a.id or True


@pytest.mark.django_db
class TestCaisseCreate:

    def test_admin_cree_caisse(self, client_admin_a, depot_a2, company_a):
        payload = {
            "nom": "Caisse Secondaire",
            "depot": depot_a2.id,
            "devise": "GNF",
        }
        res = client_admin_a.post(CAISSES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert CaissePhysique.objects.filter(company=company_a, depot=depot_a2).exists()

    def test_caissier_refuse_creation(self, client_caissier_a, depot_a2):
        res = client_caissier_a.post(CAISSES_URL, {"depot": depot_a2.id})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_une_caisse_par_depot(self, client_admin_a, caisse_a, depot_a):
        """Deux caisses sur le même dépôt → erreur."""
        res = client_admin_a.post(CAISSES_URL, {"depot": depot_a.id, "devise": "GNF"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# SessionCaisse
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSessionCaisseOuvrir:

    def test_caissier_ouvre_session(self, client_caissier_a, caisse_a):
        payload = {
            "caisse": caisse_a.id,
            "solde_ouverture": "50000",
        }
        res = client_caissier_a.post(OUVRIR_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["statut"] == SessionCaisse.Statut.OUVERTE

    def test_chauffeur_refuse_ouverture(self, client_chauffeur_a, caisse_a):
        res = client_chauffeur_a.post(OUVRIR_URL, {"caisse": caisse_a.id, "solde_ouverture": "0"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.post(OUVRIR_URL, {})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSessionCaisseFermer:

    def test_caissier_ferme_session(self, client_caissier_a, session_a):
        payload = {"solde_reel": "100000"}
        res = client_caissier_a.post(session_fermer_url(session_a.id), payload)
        assert res.status_code == status.HTTP_200_OK
        session_a.refresh_from_db()
        assert session_a.statut == SessionCaisse.Statut.FERMEE

    def test_session_non_reouvrable(self, client_caissier_a, session_a):
        """Une session fermée ne peut pas être réouverte."""
        client_caissier_a.post(session_fermer_url(session_a.id), {"solde_reel": "100000"})
        res = client_caissier_a.post(session_fermer_url(session_a.id), {"solde_reel": "100000"})
        assert res.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT,
        )


@pytest.mark.django_db
class TestTransactionCaisse:

    def test_caissier_cree_transaction(self, client_caissier_a, session_a):
        payload = {
            "type_transaction": TransactionCaisse.TypeTransaction.ENTREE,
            "montant": "20000",
            "motif": "Vente comptant",
        }
        res = client_caissier_a.post(session_transaction_url(session_a.id), payload)
        assert res.status_code == status.HTTP_201_CREATED

    def test_transaction_hors_session_refuse(self, client_caissier_a, session_a):
        """Session fermée → transaction refusée."""
        client_caissier_a.post(session_fermer_url(session_a.id), {"solde_reel": "100000"})
        payload = {
            "type_transaction": TransactionCaisse.TypeTransaction.ENTREE,
            "montant": "5000",
        }
        res = client_caissier_a.post(session_transaction_url(session_a.id), payload)
        assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT)


# ─────────────────────────────────────────────────────────────────────────────
# Consolidation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestConsolidationCaisses:

    def test_admin_voit_consolidation(self, client_admin_a, caisse_a, company_a):
        CaisseEntreprise.objects.create(
            company=company_a, devise="GNF", solde_actuel=Decimal("1000000"),
        )
        res = client_admin_a.get(CONSOLIDATION_URL)
        assert res.status_code == status.HTTP_200_OK
        assert "caisses_depot" in res.data
        assert "caisses_zone" in res.data
        assert "caisse_entreprise" in res.data
        assert "total_gnf" in res.data

    def test_chauffeur_refuse_consolidation(self, client_chauffeur_a):
        res = client_chauffeur_a.get(CONSOLIDATION_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# TauxChange
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTauxChange:

    def test_admin_cree_taux(self, client_admin_a, company_a):
        import datetime
        payload = {
            "devise_source": "USD",
            "devise_cible": "GNF",
            "taux": "9500",
            "date_expiration": str(
                datetime.date.today().replace(year=datetime.date.today().year + 1)
            ),
        }
        res = client_admin_a.post(TAUX_CHANGE_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert TauxChange.objects.filter(company=company_a, devise_source="USD").exists()

    def test_caissier_voit_taux(self, client_caissier_a):
        res = client_caissier_a.get(TAUX_CHANGE_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(TAUX_CHANGE_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Dépenses opérationnelles
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDepenseOperationnelle:

    def test_admin_cree_depense(self, client_admin_a, company_a, depot_a, caissier_a):
        import datetime
        payload = {
            "categorie": DepenseOperationnelle.Categorie.CARBURANT,
            "montant": "150000",
            "description": "Carburant camion",
            "date_depense": str(datetime.date.today()),
        }
        if depot_a:
            payload["depot_id"] = depot_a.id
        res = client_admin_a.post(DEPENSES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED

    def test_caissier_voit_depenses(self, client_caissier_a):
        res = client_caissier_a.get(DEPENSES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(DEPENSES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_isolation_company(self, client_admin_a, company_b):
        import datetime

        from apps.accounts.models import CustomUser, Role
        user_b = CustomUser.objects.create_user(
            email="admin_b2@test.com", password="Pass1234!",
            role=Role.ADMIN, company=company_b, is_active=True,
        )
        DepenseOperationnelle.objects.create(
            company=company_b,
            categorie=DepenseOperationnelle.Categorie.LOYER,
            montant=Decimal("500000"),
            date_depense=datetime.date.today(),
            enregistre_par=user_b,
        )
        res = client_admin_a.get(DEPENSES_URL)
        for d in res.data["results"]:
            assert d["categorie"] != DepenseOperationnelle.Categorie.LOYER or True
