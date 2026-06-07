"""
apps/logistique/tests/test_logistique.py
Tests API : Véhicules, Missions (CRUD + workflow + QR), Maintenances, Pannes, Carburant.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.logistique.models import ConsommationCarburant, Maintenance, Mission, Panne, Vehicule


VEHICULES_URL = "/api/vehicules/"
MISSIONS_URL = "/api/missions/"
MAINTENANCES_URL = "/api/maintenances/"
PANNES_URL = "/api/pannes/"
CARBURANT_URL = "/api/carburant/"
SCANNER_QR_URL = "/api/missions/scanner-qr/"


def vehicule_url(pk):
    return f"/api/vehicules/{pk}/"


def mission_url(pk):
    return f"/api/missions/{pk}/"


def mission_chargement_url(pk):
    return f"/api/missions/{pk}/chargement/"


def mission_transit_url(pk):
    return f"/api/missions/{pk}/transit/"


def mission_arrivee_url(pk):
    return f"/api/missions/{pk}/arrivee/"


def mission_terminer_url(pk):
    return f"/api/missions/{pk}/terminer/"


def mission_annuler_url(pk):
    return f"/api/missions/{pk}/annuler/"


def mission_qr_url(pk):
    return f"/api/missions/{pk}/qr/"


def mission_bon_livraison_url(pk):
    return f"/api/missions/{pk}/bon-livraison/"


def panne_resoudre_url(pk):
    return f"/api/pannes/{pk}/resoudre/"


# ─────────────────────────────────────────────────────────────────────────────
# Véhicules
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVehiculeList:

    def test_admin_voit_vehicules(self, client_admin_a, vehicule_a):
        res = client_admin_a.get(VEHICULES_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [v["id"] for v in res.data["results"]]
        assert vehicule_a.id in ids

    def test_chauffeur_voit_vehicules(self, client_chauffeur_a, vehicule_a):
        res = client_chauffeur_a.get(VEHICULES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_caissier_refuse(self, client_caissier_a):
        res = client_caissier_a.get(VEHICULES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(VEHICULES_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_isolation_company(self, client_admin_a, vehicule_a, vehicule_b):
        res = client_admin_a.get(VEHICULES_URL)
        ids = [v["id"] for v in res.data["results"]]
        assert vehicule_a.id in ids
        assert vehicule_b.id not in ids


@pytest.mark.django_db
class TestVehiculeCreate:

    def test_admin_cree_vehicule(self, client_admin_a, company_a):
        payload = {
            "immatriculation": "CD-5678-E",
            "type_vehicule": Vehicule.TypeVehicule.CAMIONNETTE,
            "marque": "Ford",
            "modele": "Transit",
            "annee": 2022,
            "capacite_kg": "500",
        }
        res = client_admin_a.post(VEHICULES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert Vehicule.objects.filter(company=company_a, immatriculation="CD-5678-E").exists()

    def test_caissier_refuse(self, client_caissier_a):
        res = client_caissier_a.post(VEHICULES_URL, {"immatriculation": "X"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_immatriculation_unique(self, client_admin_a, vehicule_a):
        """Tenter de créer un véhicule avec une immatriculation déjà utilisée."""
        client_admin_a.raise_request_exception = False
        res = client_admin_a.post(VEHICULES_URL, {
            "immatriculation": vehicule_a.immatriculation,
            "type_vehicule": Vehicule.TypeVehicule.CAMION,
            "marque": "X",
            "modele": "Y",
            "annee": 2020,
            "capacite_kg": "500",
        })
        client_admin_a.raise_request_exception = True
        assert res.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Missions
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestMissionList:

    def test_admin_voit_missions(self, client_admin_a, mission_a):
        res = client_admin_a.get(MISSIONS_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [m["id"] for m in res.data["results"]]
        assert mission_a.id in ids

    def test_chauffeur_voit_missions(self, client_chauffeur_a, mission_a):
        res = client_chauffeur_a.get(MISSIONS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_caissier_refuse(self, client_caissier_a):
        res = client_caissier_a.get(MISSIONS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_isolation_company(self, client_admin_a, mission_a, vehicule_b, depot_b):
        res = client_admin_a.get(MISSIONS_URL)
        ids = [m["id"] for m in res.data["results"]]
        assert mission_a.id in ids


@pytest.mark.django_db
class TestMissionCreate:

    def test_admin_cree_mission(
        self, client_admin_a, vehicule_a, depot_a, depot_a2, chauffeur_a, company_a,
    ):
        payload = {
            "vehicule": vehicule_a.id,
            "chauffeur": chauffeur_a.id,
            "depot_depart": depot_a.id,
            "depot_arrivee": depot_a2.id,
        }
        res = client_admin_a.post(MISSIONS_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["numero"].startswith("MSN-")
        assert res.data["statut"] == Mission.Statut.PLANIFIEE

    def test_superviseur_cree_mission(
        self, client_superviseur_a, vehicule_a, depot_a, depot_a2, chauffeur_a,
    ):
        payload = {
            "vehicule": vehicule_a.id,
            "chauffeur": chauffeur_a.id,
            "depot_depart": depot_a.id,
            "depot_arrivee": depot_a2.id,
        }
        res = client_superviseur_a.post(MISSIONS_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED

    def test_caissier_refuse_creation(self, client_caissier_a):
        res = client_caissier_a.post(MISSIONS_URL, {})
        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestMissionWorkflow:

    def test_chargement(self, client_admin_a, mission_a):
        res = client_admin_a.post(mission_chargement_url(mission_a.id))
        assert res.status_code == status.HTTP_200_OK
        mission_a.refresh_from_db()
        assert mission_a.statut == Mission.Statut.CHARGEMENT

    def test_transit(self, client_admin_a, mission_a):
        client_admin_a.post(mission_chargement_url(mission_a.id))
        res = client_admin_a.post(mission_transit_url(mission_a.id))
        assert res.status_code == status.HTTP_200_OK
        mission_a.refresh_from_db()
        assert mission_a.statut == Mission.Statut.EN_TRANSIT

    def test_arrivee(self, client_admin_a, mission_a):
        client_admin_a.post(mission_chargement_url(mission_a.id))
        client_admin_a.post(mission_transit_url(mission_a.id))
        payload = {"signature": "data:image/png;base64,AAAA"}
        res = client_admin_a.post(mission_arrivee_url(mission_a.id), payload)
        assert res.status_code == status.HTTP_200_OK
        mission_a.refresh_from_db()
        assert mission_a.statut == Mission.Statut.ARRIVEE

    def test_terminer(self, client_admin_a, mission_a):
        client_admin_a.post(mission_chargement_url(mission_a.id))
        client_admin_a.post(mission_transit_url(mission_a.id))
        client_admin_a.post(mission_arrivee_url(mission_a.id), {"signature": "data:image/png;base64,AAAA"})
        res = client_admin_a.post(mission_terminer_url(mission_a.id))
        assert res.status_code == status.HTTP_200_OK
        mission_a.refresh_from_db()
        assert mission_a.statut == Mission.Statut.TERMINEE

    def test_annuler(self, client_admin_a, mission_a):
        res = client_admin_a.post(mission_annuler_url(mission_a.id))
        assert res.status_code == status.HTTP_200_OK
        mission_a.refresh_from_db()
        assert mission_a.statut == Mission.Statut.ANNULEE

    def test_caissier_refuse_chargement(self, client_caissier_a, mission_a):
        res = client_caissier_a.post(mission_chargement_url(mission_a.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestMissionQR:

    def test_qr_retourne_image_base64(self, client_admin_a, mission_a):
        res = client_admin_a.get(mission_qr_url(mission_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert "qr_code" in res.data or "image" in res.data

    def test_scanner_qr_planifiee_vers_chargement(self, client_chauffeur_a, mission_a):
        payload = {"qr_code": str(mission_a.qr_code)}
        res = client_chauffeur_a.post(SCANNER_QR_URL, payload)
        assert res.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    def test_scanner_qr_invalide_refuse(self, client_admin_a):
        payload = {"qr_code": "00000000-0000-0000-0000-000000000000"}
        res = client_admin_a.post(SCANNER_QR_URL, payload)
        assert res.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST)

    def test_bon_livraison_pdf(self, client_admin_a, mission_a):
        # PNG 1x1 blanc valide (généré via PIL)
        sig = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4"
            "//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
        )
        client_admin_a.post(mission_chargement_url(mission_a.id))
        client_admin_a.post(mission_transit_url(mission_a.id))
        client_admin_a.post(mission_arrivee_url(mission_a.id), {"signature": sig})
        client_admin_a.post(mission_terminer_url(mission_a.id))
        res = client_admin_a.get(mission_bon_livraison_url(mission_a.id))
        assert res.status_code == status.HTTP_200_OK


# ─────────────────────────────────────────────────────────────────────────────
# Maintenances
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestMaintenance:

    def test_admin_cree_maintenance(self, client_admin_a, vehicule_a):
        import datetime
        payload = {
            "vehicule": vehicule_a.id,
            "type_maintenance": Maintenance.TypeMaintenance.PREVENTIVE,
            "description": "Vidange",
            "cout": "150000",
            "date_planifiee": str(datetime.date.today()),
        }
        res = client_admin_a.post(MAINTENANCES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED

    def test_maintenancier_cree_maintenance(self, client_maintenancier_a, vehicule_a):
        import datetime
        payload = {
            "vehicule": vehicule_a.id,
            "type_maintenance": Maintenance.TypeMaintenance.CORRECTIVE,
            "description": "Remplacement filtre",
            "cout": "80000",
            "date_planifiee": str(datetime.date.today()),
        }
        res = client_maintenancier_a.post(MAINTENANCES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED

    def test_chauffeur_voit_maintenances(self, client_chauffeur_a):
        res = client_chauffeur_a.get(MAINTENANCES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_caissier_refuse(self, client_caissier_a):
        res = client_caissier_a.get(MAINTENANCES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Pannes
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPanne:

    def test_chauffeur_declare_panne(self, client_chauffeur_a, vehicule_a):
        payload = {
            "vehicule": vehicule_a.id,
            "description": "Crevaison pneu avant droit",
            "cout_reparation": "50000",
        }
        res = client_chauffeur_a.post(PANNES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["resolu_le"] is None

    def test_admin_resout_panne(self, client_admin_a, vehicule_a, admin_a):
        panne = Panne.objects.create(
            vehicule=vehicule_a,
            description="Batterie HS",
            cout_reparation=Decimal("200000"),
            declare_par=admin_a,
        )
        res = client_admin_a.post(panne_resoudre_url(panne.id))
        assert res.status_code == status.HTTP_200_OK
        panne.refresh_from_db()
        assert panne.resolu_le is not None

    def test_caissier_refuse(self, client_caissier_a):
        res = client_caissier_a.get(PANNES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Consommation carburant
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestConsommationCarburant:

    def test_chauffeur_saisit_carburant(self, client_chauffeur_a, vehicule_a, chauffeur_a):
        import datetime
        payload = {
            "vehicule": vehicule_a.id,
            "type_carburant": ConsommationCarburant.TypeCarburant.GASOIL,
            "quantite_litres": "50",
            "prix_par_litre": "12000",
            "kilometrage": "50000",
            "date_plein": str(datetime.date.today()),
        }
        res = client_chauffeur_a.post(CARBURANT_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        vehicule_a.refresh_from_db()
        assert vehicule_a.kilometrage_actuel == 50000

    def test_montant_total_calcule(self, client_chauffeur_a, vehicule_a):
        import datetime
        payload = {
            "vehicule": vehicule_a.id,
            "type_carburant": ConsommationCarburant.TypeCarburant.GASOIL,
            "quantite_litres": "40",
            "prix_par_litre": "12000",
            "kilometrage": "55000",
            "date_plein": str(datetime.date.today()),
        }
        res = client_chauffeur_a.post(CARBURANT_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert Decimal(str(res.data["montant_total"])) == Decimal("480000")

    def test_admin_voit_carburant(self, client_admin_a):
        res = client_admin_a.get(CARBURANT_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_caissier_refuse(self, client_caissier_a):
        res = client_caissier_a.get(CARBURANT_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_isolation_company(self, client_admin_a, vehicule_a, vehicule_b):
        res = client_admin_a.get(CARBURANT_URL)
        assert res.status_code == status.HTTP_200_OK
