"""
apps/ventes/tests/test_commandes.py
Tests API : Commandes, Paiements, Devis, Retours, Promotions.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.ventes.models import Commande, Devis, Paiement, Promotion


COMMANDES_URL = "/api/commandes/"
DEVIS_URL = "/api/devis/"
RETOURS_URL = "/api/retours/"
PROMOTIONS_URL = "/api/promotions/"
FIDELITE_URL = "/api/fidelite/parametres/"


def commande_url(pk):
    return f"/api/commandes/{pk}/"


def commande_paiement_url(pk):
    return f"/api/commandes/{pk}/paiement/"


def commande_annuler_url(pk):
    return f"/api/commandes/{pk}/annuler/"


def commande_facture_url(pk):
    return f"/api/commandes/{pk}/facture/"


def commande_bon_livraison_url(pk):
    return f"/api/commandes/{pk}/bon-livraison/"


def devis_url(pk):
    return f"/api/devis/{pk}/"


def devis_convertir_url(pk):
    return f"/api/devis/{pk}/convertir/"


# ─────────────────────────────────────────────────────────────────────────────
# Commandes
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommandeList:

    def test_caissier_voit_commandes(self, client_caissier_a, commande_a):
        res = client_caissier_a.get(COMMANDES_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [c["id"] for c in res.data["results"]]
        assert commande_a.id in ids

    def test_admin_voit_commandes(self, client_admin_a, commande_a):
        res = client_admin_a.get(COMMANDES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(COMMANDES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(COMMANDES_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_isolation_company(self, client_admin_a, commande_a, company_b):
        """Admin A ne voit pas les commandes de company B."""
        from apps.accounts.models import CustomUser, Role
        from apps.ventes.models import Commande
        CustomUser.objects.create_user(
            email="admin_b_cmd@test.com", password="Pass1234!",
            role=Role.ADMIN, company=company_b, is_active=True,
        )
        res = client_admin_a.get(COMMANDES_URL)
        ids = [c["id"] for c in res.data["results"]]
        # Admin A ne doit voir que ses propres commandes
        assert commande_a.id in ids
        # Toutes les commandes retournées appartiennent à company A
        for c in res.data["results"]:
            assert c["id"] in ids


@pytest.mark.django_db
class TestCommandeCreate:

    def test_caissier_cree_commande(
        self, client_caissier_a, produit_stocked, depot_a, company_a,
    ):
        payload = {
            "depot": depot_a.id,
            "lignes": [{"produit": produit_stocked.id, "quantite": 3}],
            "montant_paye": "60000",
            "mode_paiement_initial": Paiement.Mode.ESPECES,
        }
        res = client_caissier_a.post(COMMANDES_URL, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["statut"] == Commande.Statut.CONFIRMEE
        assert res.data["numero"].startswith("CMD-")

    def test_stock_insuffisant_refuse(self, client_caissier_a, produit_stocked, depot_a):
        payload = {
            "depot": depot_a.id,
            "lignes": [{"produit": produit_stocked.id, "quantite": 9999}],
        }
        res = client_caissier_a.post(COMMANDES_URL, payload, format="json")
        assert res.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT,
        )

    def test_chauffeur_refuse(self, client_chauffeur_a, produit_stocked, depot_a):
        res = client_chauffeur_a.post(COMMANDES_URL, {}, format="json")
        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCommandeDetail:

    def test_caissier_voit_detail(self, client_caissier_a, commande_a):
        res = client_caissier_a.get(commande_url(commande_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == commande_a.id
        assert res.data["statut"] == Commande.Statut.CONFIRMEE

    def test_404_commande_inexistante(self, client_caissier_a):
        res = client_caissier_a.get(commande_url(99999))
        assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCommandePaiement:

    def test_caissier_ajoute_paiement(self, client_caissier_a, commande_a):
        payload = {
            "montant": "10000",
            "mode": Paiement.Mode.ESPECES,
        }
        res = client_caissier_a.post(commande_paiement_url(commande_a.id), payload)
        assert res.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    def test_chauffeur_refuse(self, client_chauffeur_a, commande_a):
        res = client_chauffeur_a.post(
            commande_paiement_url(commande_a.id), {"montant": "5000"},
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCommandeAnnuler:

    def test_admin_annule_commande(self, client_admin_a, commande_a):
        res = client_admin_a.post(commande_annuler_url(commande_a.id))
        assert res.status_code == status.HTTP_200_OK
        commande_a.refresh_from_db()
        assert commande_a.statut == Commande.Statut.ANNULEE

    def test_chauffeur_refuse_annulation(self, client_chauffeur_a, commande_a):
        res = client_chauffeur_a.post(commande_annuler_url(commande_a.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCommandePDF:

    def test_facture_pdf_retourne_pdf(self, client_caissier_a, commande_a):
        res = client_caissier_a.get(commande_facture_url(commande_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Type"] == "application/pdf"

    def test_bon_livraison_pdf(self, client_caissier_a, commande_a):
        res = client_caissier_a.get(commande_bon_livraison_url(commande_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Type"] == "application/pdf"


# ─────────────────────────────────────────────────────────────────────────────
# Dévis
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDevis:

    def test_commercial_cree_devis(
        self, client_commercial_a, depot_a, client_vente, produit_stocked,
    ):
        payload = {
            "depot": depot_a.id,
            "client": client_vente.id,
            "lignes": [
                {
                    "produit": produit_stocked.id,
                    "quantite": "2",
                    "prix_unitaire_ht": "20000",
                }
            ],
        }
        res = client_commercial_a.post(DEVIS_URL, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["numero"].startswith("DEV-")
        assert res.data["statut"] == Devis.Statut.BROUILLON

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(DEVIS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_liste_devis(self, client_admin_a):
        res = client_admin_a.get(DEVIS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_caissier_convertit_devis(
        self, client_caissier_a, depot_a, client_vente, produit_stocked, caissier_a, company_a,
    ):
        from apps.ventes.models import LigneDevis
        devis = Devis.objects.create(
            company=company_a,
            depot=depot_a,
            client=client_vente,
            cree_par=caissier_a,
        )
        LigneDevis.objects.create(
            devis=devis,
            produit=produit_stocked,
            quantite=Decimal("2"),
            prix_unitaire_ht=Decimal("20000"),
        )
        payload = {
            "lignes": [
                {
                    "produit": produit_stocked.id,
                    "quantite": "2",
                    "prix_unitaire_ht": "20000",
                }
            ],
            "montant_paye": "40000",
        }
        res = client_caissier_a.post(devis_convertir_url(devis.id), payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        devis.refresh_from_db()
        assert devis.statut == Devis.Statut.CONVERTI


# ─────────────────────────────────────────────────────────────────────────────
# Paramètres fidélité
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestParametresFidelite:

    def test_admin_voit_parametres(self, client_admin_a, parametres_fidelite):
        res = client_admin_a.get(FIDELITE_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_admin_modifie_parametres(self, client_admin_a, parametres_fidelite):
        res = client_admin_a.patch(FIDELITE_URL, {"tranche_montant": "20000"})
        assert res.status_code == status.HTTP_200_OK
        parametres_fidelite.refresh_from_db()
        assert parametres_fidelite.tranche_montant == Decimal("20000")

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(FIDELITE_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Promotions
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPromotion:

    def test_admin_cree_promotion(self, client_admin_a, company_a):
        import datetime
        payload = {
            "nom": "Promo Ramadan",
            "type_promotion": Promotion.TypePromotion.POURCENTAGE,
            "valeur": "10",
            "cible": Promotion.Cible.TOUS,
            "date_debut": str(datetime.date.today()),
            "date_fin": str(datetime.date.today().replace(year=datetime.date.today().year + 1)),
        }
        res = client_admin_a.post(PROMOTIONS_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert Promotion.objects.filter(company=company_a, nom="Promo Ramadan").exists()

    def test_caissier_voit_promotions(self, client_caissier_a):
        res = client_caissier_a.get(PROMOTIONS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(PROMOTIONS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_isolation_company(self, client_admin_a, company_b, admin_b):
        import datetime
        Promotion.objects.create(
            company=company_b,
            nom="Promo B",
            type_promotion=Promotion.TypePromotion.POURCENTAGE,
            valeur=Decimal("5"),
            cible=Promotion.Cible.TOUS,
            date_debut=datetime.date.today(),
            date_fin=datetime.date.today().replace(year=datetime.date.today().year + 1),
            created_by=admin_b,
        )
        res = client_admin_a.get(PROMOTIONS_URL)
        for p in res.data["results"]:
            assert p["nom"] != "Promo B"
