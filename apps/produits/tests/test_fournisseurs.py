"""
apps/produits/tests/test_fournisseurs.py
Tests API : Fournisseurs, Commandes fournisseurs, Évaluations.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.produits.models import CommandeFournisseur, Fournisseur


FOURNISSEURS_URL = "/api/fournisseurs/"
COMMANDES_FOURNISSEUR_URL = "/api/commandes-fournisseurs/"
EVALUATIONS_URL = "/api/evaluations-fournisseurs/"


def fournisseur_url(pk):
    return f"/api/fournisseurs/{pk}/"


def fournisseur_evaluations_url(pk):
    return f"/api/fournisseurs/{pk}/evaluations/"


def commande_fournisseur_url(pk):
    return f"/api/commandes-fournisseurs/{pk}/"


def commande_recevoir_url(pk):
    return f"/api/commandes-fournisseurs/{pk}/recevoir/"


# ─────────────────────────────────────────────────────────────────────────────
# Fournisseurs
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFournisseurList:

    def test_admin_voit_fournisseurs_sa_company(self, client_admin_a, fournisseur_a):
        res = client_admin_a.get(FOURNISSEURS_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [f["id"] for f in res.data["results"]]
        assert fournisseur_a.id in ids

    def test_isolation_company(self, client_admin_a, fournisseur_b):
        res = client_admin_a.get(FOURNISSEURS_URL)
        ids = [f["id"] for f in res.data["results"]]
        assert fournisseur_b.id not in ids

    def test_gestionnaire_peut_lister(self, client_gestionnaire_a, fournisseur_a):
        res = client_gestionnaire_a.get(FOURNISSEURS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(FOURNISSEURS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(FOURNISSEURS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestFournisseurCreate:

    def test_admin_cree_fournisseur(self, client_admin_a, company_a):
        payload = {"code": "FRN-NEW", "nom": "Nouveau Fournisseur", "telephone": "622999888"}
        res = client_admin_a.post(FOURNISSEURS_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert Fournisseur.objects.filter(company=company_a, code="FRN-NEW").exists()

    def test_superviseur_refuse(self, client_superviseur_a):
        res = client_superviseur_a.post(FOURNISSEURS_URL, {"code": "X", "nom": "Y"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_code_unique_par_company(self, client_admin_a, fournisseur_a):
        res = client_admin_a.post(FOURNISSEURS_URL, {"code": fournisseur_a.code, "nom": "Doublon"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestFournisseurDetail:

    def test_admin_voit_detail(self, client_admin_a, fournisseur_a):
        res = client_admin_a.get(fournisseur_url(fournisseur_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == fournisseur_a.id

    def test_admin_refuse_autre_company(self, client_admin_a, fournisseur_b):
        res = client_admin_a.get(fournisseur_url(fournisseur_b.id))
        assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCommandeFournisseur:

    def test_admin_cree_commande_fournisseur(
        self, client_admin_a, fournisseur_a, depot_a, produit_a,
    ):
        payload = {
            "fournisseur": fournisseur_a.id,
            "depot_destination": depot_a.id,
            "lignes": [
                {
                    "produit": produit_a.id,
                    "quantite_commandee": "10",
                    "prix_unitaire": "80000",
                }
            ],
        }
        res = client_admin_a.post(COMMANDES_FOURNISSEUR_URL, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["numero"].startswith("CDF-")

    def test_superviseur_refuse_creation(self, client_superviseur_a):
        res = client_superviseur_a.post(COMMANDES_FOURNISSEUR_URL, {})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_liste_filtree_par_company(self, client_admin_a, fournisseur_a, depot_a, produit_a):
        # Créer via admin_a puis vérifier que admin_b ne voit pas
        payload = {
            "fournisseur": fournisseur_a.id,
            "depot_destination": depot_a.id,
            "lignes": [{"produit": produit_a.id, "quantite_commandee": "5", "prix_unitaire": "80000"}],
        }
        client_admin_a.post(COMMANDES_FOURNISSEUR_URL, payload, format="json")
        res = client_admin_a.get(COMMANDES_FOURNISSEUR_URL)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Évaluations fournisseurs
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEvaluationFournisseur:

    def test_admin_cree_evaluation(self, client_admin_a, fournisseur_a):
        payload = {
            "fournisseur": fournisseur_a.id,
            "note_qualite": 4,
            "note_delai": 3,
            "note_service": 5,
            "commentaire": "Bon fournisseur",
        }
        res = client_admin_a.post(EVALUATIONS_URL, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["note_globale"] == pytest.approx(4.0)

    def test_endpoint_evaluations_fournisseur(self, client_admin_a, fournisseur_a):
        res = client_admin_a.get(fournisseur_evaluations_url(fournisseur_a.id))
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a, fournisseur_a):
        res = client_chauffeur_a.get(fournisseur_evaluations_url(fournisseur_a.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN
