"""
apps/stocks/tests/test_transferts.py
Tests API : TransfertStock (CRUD + workflow), Inventaires, Ajustements.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.stocks.models import AjustementStock, Inventaire, TransfertStock


TRANSFERTS_URL = "/api/transferts/"
INVENTAIRES_URL = "/api/inventaires/"
AJUSTEMENTS_URL = "/api/ajustements-stock/"


def transfert_url(pk):
    return f"/api/transferts/{pk}/"


def transfert_expedier_url(pk):
    return f"/api/transferts/{pk}/expedier/"


def transfert_receptionner_url(pk):
    return f"/api/transferts/{pk}/receptionner/"


def transfert_annuler_url(pk):
    return f"/api/transferts/{pk}/annuler/"


def inventaire_url(pk):
    return f"/api/inventaires/{pk}/"


def inventaire_valider_url(pk):
    return f"/api/inventaires/{pk}/valider/"


def ajustement_url(pk):
    return f"/api/ajustements-stock/{pk}/"


def ajustement_approuver_url(pk):
    return f"/api/ajustements-stock/{pk}/approuver/"


def ajustement_refuser_url(pk):
    return f"/api/ajustements-stock/{pk}/refuser/"


# ─────────────────────────────────────────────────────────────────────────────
# TransfertStock
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTransfertList:

    def test_gestionnaire_voit_transferts(
        self, client_gestionnaire_a, gestionnaire_a, stock_a, depot_a, depot_a2,
    ):
        TransfertStock.objects.create(
            company=depot_a.zone.company,
            depot_source=depot_a,
            depot_destination=depot_a2,
            utilisateur_envoi=gestionnaire_a,
        )
        res = client_gestionnaire_a.get(TRANSFERTS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_caissier_refuse(self, client_caissier_a):
        res = client_caissier_a.get(TRANSFERTS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(TRANSFERTS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTransfertCreate:

    def test_admin_cree_transfert(
        self, client_admin_a, depot_a, depot_a2, produit_a, stock_a,
    ):
        payload = {
            "depot_source": depot_a.id,
            "depot_destination": depot_a2.id,
            "lignes": [
                {"produit": produit_a.id, "quantite_envoyee": "5"},
            ],
        }
        res = client_admin_a.post(TRANSFERTS_URL, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["numero"].startswith("TRF-")
        assert res.data["statut"] == TransfertStock.Statut.BROUILLON

    def test_gestionnaire_cree_transfert(
        self, client_gestionnaire_a, depot_a, depot_a2, produit_a, stock_a,
    ):
        payload = {
            "depot_source": depot_a.id,
            "depot_destination": depot_a2.id,
            "lignes": [{"produit": produit_a.id, "quantite_envoyee": "3"}],
        }
        res = client_gestionnaire_a.post(TRANSFERTS_URL, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED

    def test_superviseur_refuse_creation(self, client_superviseur_a, depot_a, depot_a2):
        res = client_superviseur_a.post(TRANSFERTS_URL, {}, format="json")
        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTransfertWorkflow:

    @pytest.fixture
    def transfert(self, admin_a, depot_a, depot_a2, produit_a, stock_a, company_a):
        from apps.stocks.services import creer_transfert
        t = creer_transfert(
            company=company_a,
            depot_source=depot_a,
            depot_destination=depot_a2,
            lignes_data=[{"produit": produit_a, "quantite_envoyee": Decimal("5")}],
            utilisateur=admin_a,
        )
        return t

    def test_expedier_transfert(self, client_gestionnaire_a, transfert):
        res = client_gestionnaire_a.post(transfert_expedier_url(transfert.id))
        assert res.status_code == status.HTTP_200_OK
        transfert.refresh_from_db()
        assert transfert.statut == TransfertStock.Statut.EN_TRANSIT

    def test_receptionner_transfert(self, client_gestionnaire_a, transfert):
        from apps.stocks.models import LigneTransfert
        client_gestionnaire_a.post(transfert_expedier_url(transfert.id))
        ligne = LigneTransfert.objects.filter(transfert=transfert).first()
        payload = {
            "lignes": [{"ligne_id": ligne.id, "quantite_recue": 5}],
        }
        res = client_gestionnaire_a.post(
            transfert_receptionner_url(transfert.id), payload, format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        transfert.refresh_from_db()
        assert transfert.statut == TransfertStock.Statut.RECU

    def test_annuler_transfert(self, client_admin_a, transfert):
        res = client_admin_a.post(transfert_annuler_url(transfert.id))
        assert res.status_code == status.HTTP_200_OK
        transfert.refresh_from_db()
        assert transfert.statut == TransfertStock.Statut.ANNULE

    def test_caissier_refuse_expedition(self, client_caissier_a, transfert):
        res = client_caissier_a.post(transfert_expedier_url(transfert.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Inventaires
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestInventaireList:

    def test_gestionnaire_voit_inventaires(self, client_gestionnaire_a):
        res = client_gestionnaire_a.get(INVENTAIRES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_caissier_refuse(self, client_caissier_a):
        res = client_caissier_a.get(INVENTAIRES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestInventaireCreate:

    def test_admin_cree_inventaire(self, client_admin_a, depot_a, company_a):
        payload = {"depot": depot_a.id}
        res = client_admin_a.post(INVENTAIRES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["numero"].startswith("INV-")

    def test_superviseur_cree_inventaire(self, client_superviseur_a, depot_a):
        res = client_superviseur_a.post(INVENTAIRES_URL, {"depot": depot_a.id})
        assert res.status_code == status.HTTP_201_CREATED

    def test_gestionnaire_peut_creer_inventaire(self, client_gestionnaire_a, depot_a):
        """Le gestionnaire de stock peut initier un inventaire physique de son dépôt."""
        res = client_gestionnaire_a.post(INVENTAIRES_URL, {"depot": depot_a.id})
        assert res.status_code == status.HTTP_201_CREATED


# ─────────────────────────────────────────────────────────────────────────────
# Ajustements stock
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAjustementStock:

    def test_gestionnaire_cree_ajustement(
        self, client_gestionnaire_a, depot_a, produit_a, stock_a, company_a,
    ):
        payload = {
            "depot": depot_a.id,
            "produit": produit_a.id,
            "quantite": "5",
            "motif": "Casse",
        }
        res = client_gestionnaire_a.post(AJUSTEMENTS_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["statut"] == AjustementStock.Statut.EN_ATTENTE

    def test_admin_approuve_ajustement(
        self, client_admin_a, depot_a, produit_a, stock_a, gestionnaire_a, company_a,
    ):
        ajust = AjustementStock.objects.create(
            company=company_a,
            depot=depot_a,
            produit=produit_a,
            quantite=Decimal("-3"),
            motif="Perte",
            demande_par=gestionnaire_a,
        )
        res = client_admin_a.post(ajustement_approuver_url(ajust.id))
        assert res.status_code == status.HTTP_200_OK
        ajust.refresh_from_db()
        assert ajust.statut == AjustementStock.Statut.APPROUVE

    def test_admin_refuse_ajustement(
        self, client_admin_a, depot_a, produit_a, gestionnaire_a, company_a,
    ):
        ajust = AjustementStock.objects.create(
            company=company_a,
            depot=depot_a,
            produit=produit_a,
            quantite=Decimal("10"),
            motif="Erreur",
            demande_par=gestionnaire_a,
        )
        res = client_admin_a.post(ajustement_refuser_url(ajust.id))
        assert res.status_code == status.HTTP_200_OK
        ajust.refresh_from_db()
        assert ajust.statut == AjustementStock.Statut.REFUSE

    def test_caissier_refuse_creation(self, client_caissier_a, depot_a, produit_a):
        res = client_caissier_a.post(AJUSTEMENTS_URL, {
            "depot_id": depot_a.id, "produit_id": produit_a.id, "quantite": "1", "motif": "X",
        })
        assert res.status_code == status.HTTP_403_FORBIDDEN
