"""
apps/accounts/tests/test_zones_depots.py
R1-B08 — Tests complets CRUD Zones et Dépôts.
Lancer : pytest apps/accounts/tests/test_zones_depots.py -v
"""

import pytest
from rest_framework import status

from apps.companies.models import Depot, Zone

ZONES_URL = "/api/zones/"
DEPOTS_URL = "/api/depots/"


def zone_url(pk):
    return f"/api/zones/{pk}/"


def depot_url(pk):
    return f"/api/depots/{pk}/"


def depot_dashboard_url(pk):
    return f"/api/depots/{pk}/dashboard/"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/zones/ — Liste
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestZoneList:

    def test_admin_voit_zones_sa_company(self, client_admin_a, zone_a, zone_b):
        res = client_admin_a.get(ZONES_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [z["id"] for z in res.data["results"]]
        assert zone_a.id in ids
        assert zone_b.id not in ids

    def test_superviseur_peut_lister(self, client_superviseur_a, zone_a):
        res = client_superviseur_a.get(ZONES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_commercial_refuse(self, client_commercial_a):
        res = client_commercial_a.get(ZONES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(ZONES_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_superadmin_voit_toutes_les_zones(self, client_superadmin, zone_a, zone_b):
        res = client_superadmin.get(ZONES_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [z["id"] for z in res.data["results"]]
        assert zone_a.id in ids
        assert zone_b.id in ids

    def test_filtre_is_active(self, client_admin_a, company_a):
        inactive = Zone.objects.create(company=company_a, name="Zone Inactive", code="ZI", is_active=False)
        res = client_admin_a.get(ZONES_URL, {"is_active": "false"})
        assert res.status_code == status.HTTP_200_OK
        ids = [z["id"] for z in res.data["results"]]
        assert inactive.id in ids

    def test_liste_contient_depot_count(self, client_admin_a, zone_a, depot_a, depot_a2):
        res = client_admin_a.get(ZONES_URL)
        zone_data = next(z for z in res.data["results"] if z["id"] == zone_a.id)
        assert zone_data["depot_count"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/zones/{id}/ — Détail
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestZoneDetail:

    def test_admin_voit_detail_sa_zone(self, client_admin_a, zone_a, depot_a):
        res = client_admin_a.get(zone_url(zone_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == zone_a.id
        # Dépôts imbriqués présents
        assert len(res.data["depots"]) == 1
        assert res.data["depots"][0]["id"] == depot_a.id

    def test_admin_refuse_zone_autre_company(self, client_admin_a, zone_b):
        res = client_admin_a.get(zone_url(zone_b.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_404_zone_inexistante(self, client_admin_a):
        res = client_admin_a.get(zone_url(99999))
        assert res.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/zones/ — Création
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestZoneCreate:

    def get_payload(self, **kwargs):
        data = {"name": "Nouvelle Zone", "code": "NZ", "description": "Test"}
        data.update(kwargs)
        return data

    def test_admin_cree_zone(self, client_admin_a, company_a):
        res = client_admin_a.post(ZONES_URL, self.get_payload())
        assert res.status_code == status.HTTP_201_CREATED
        zone = Zone.objects.get(code="NZ")
        assert zone.company == company_a

    def test_superviseur_refuse_creation(self, client_superviseur_a):
        res = client_superviseur_a.post(ZONES_URL, self.get_payload())
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_code_unique_refuse(self, client_admin_a, zone_a):
        res = client_admin_a.post(ZONES_URL, self.get_payload(code=zone_a.code))
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "code" in res.data

    def test_nom_unique_par_company_refuse(self, client_admin_a, zone_a):
        res = client_admin_a.post(ZONES_URL, self.get_payload(name=zone_a.name, code="NEWCODE"))
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_meme_nom_autre_company_accepte(self, client_admin_b, zone_a):
        """Le même nom est autorisé dans une autre company."""
        res = client_admin_b.post(ZONES_URL, {"name": zone_a.name, "code": "ZXX"})
        assert res.status_code == status.HTTP_201_CREATED

    def test_code_mis_en_majuscules(self, client_admin_a):
        res = client_admin_a.post(ZONES_URL, self.get_payload(code="minuscule"))
        assert res.status_code == status.HTTP_201_CREATED
        assert Zone.objects.get(id=res.data["id"]).code == "MINUSCULE"

    def test_champs_obligatoires_manquants(self, client_admin_a):
        res = client_admin_a.post(ZONES_URL, {})
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/zones/{id}/ — Modification
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestZoneUpdate:

    def test_admin_modifie_zone(self, client_admin_a, zone_a):
        res = client_admin_a.patch(zone_url(zone_a.id), {"description": "Modifiée"})
        assert res.status_code == status.HTTP_200_OK
        zone_a.refresh_from_db()
        assert zone_a.description == "Modifiée"

    def test_admin_refuse_zone_autre_company(self, client_admin_a, zone_b):
        res = client_admin_a.patch(zone_url(zone_b.id), {"description": "Hack"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_superviseur_refuse(self, client_superviseur_a, zone_a):
        res = client_superviseur_a.patch(zone_url(zone_a.id), {"description": "Hack"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_code_unique_refuse_sur_update(self, client_admin_a, zone_a, zone_a2):
        res = client_admin_a.patch(zone_url(zone_a.id), {"code": zone_a2.code})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_partiel_preserves_autres_champs(self, client_admin_a, zone_a):
        nom_original = zone_a.name
        res = client_admin_a.patch(zone_url(zone_a.id), {"description": "Nouveau"})
        assert res.status_code == status.HTTP_200_OK
        zone_a.refresh_from_db()
        assert zone_a.name == nom_original


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/zones/{id}/ — Désactivation soft
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestZoneDestroy:

    def test_admin_desactive_zone(self, client_admin_a, zone_a):
        res = client_admin_a.delete(zone_url(zone_a.id))
        assert res.status_code == status.HTTP_200_OK
        zone_a.refresh_from_db()
        assert zone_a.is_active is False

    def test_suppression_physique_impossible(self, client_admin_a, zone_a):
        client_admin_a.delete(zone_url(zone_a.id))
        assert Zone.objects.filter(id=zone_a.id).exists()

    def test_admin_refuse_zone_autre_company(self, client_admin_a, zone_b):
        res = client_admin_a.delete(zone_url(zone_b.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_superviseur_refuse(self, client_superviseur_a, zone_a):
        res = client_superviseur_a.delete(zone_url(zone_a.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_depots_non_desactives_automatiquement(self, client_admin_a, zone_a, depot_a):
        """Désactiver une zone ne désactive pas ses dépôts."""
        client_admin_a.delete(zone_url(zone_a.id))
        depot_a.refresh_from_db()
        assert depot_a.is_active is True


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/depots/ — Liste
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDepotList:

    def test_admin_voit_depots_sa_company(self, client_admin_a, depot_a, depot_b):
        res = client_admin_a.get(DEPOTS_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [d["id"] for d in res.data["results"]]
        assert depot_a.id in ids
        assert depot_b.id not in ids

    def test_filtre_par_zone(self, client_admin_a, zone_a, zone_a2, depot_a, depot_a2):
        # depot_a2 est dans zone_a, on filtre par zone_a2 qui est vide
        res = client_admin_a.get(DEPOTS_URL, {"zone": zone_a2.id})
        assert res.status_code == status.HTTP_200_OK
        ids = [d["id"] for d in res.data["results"]]
        assert depot_a.id not in ids

    def test_filtre_is_active(self, client_admin_a, zone_a):
        inactive = Depot.objects.create(zone=zone_a, name="Dépôt Inactif", code="DI", is_active=False)
        res = client_admin_a.get(DEPOTS_URL, {"is_active": "false"})
        ids = [d["id"] for d in res.data["results"]]
        assert inactive.id in ids

    def test_commercial_refuse(self, client_commercial_a):
        res = client_commercial_a.get(DEPOTS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_superadmin_voit_tous_depots(self, client_superadmin, depot_a, depot_b):
        res = client_superadmin.get(DEPOTS_URL)
        ids = [d["id"] for d in res.data["results"]]
        assert depot_a.id in ids
        assert depot_b.id in ids


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/depots/{id}/ — Détail
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDepotDetail:

    def test_admin_voit_depot_sa_company(self, client_admin_a, depot_a):
        res = client_admin_a.get(depot_url(depot_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == depot_a.id
        assert res.data["zone_id"] == depot_a.zone_id

    def test_admin_refuse_depot_autre_company(self, client_admin_a, depot_b):
        res = client_admin_a.get(depot_url(depot_b.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_404_depot_inexistant(self, client_admin_a):
        res = client_admin_a.get(depot_url(99999))
        assert res.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/depots/ — Création
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDepotCreate:

    def get_payload(self, zone_id, **kwargs):
        data = {"name": "Nouveau Dépôt", "code": "ND", "zone_id": zone_id}
        data.update(kwargs)
        return data

    def test_admin_cree_depot(self, client_admin_a, zone_a):
        res = client_admin_a.post(DEPOTS_URL, self.get_payload(zone_a.id))
        assert res.status_code == status.HTTP_201_CREATED
        assert Depot.objects.filter(code="ND").exists()

    def test_zone_autre_company_refuse(self, client_admin_a, zone_b):
        """Un admin ne peut pas créer un dépôt dans une zone d'une autre company."""
        res = client_admin_a.post(DEPOTS_URL, self.get_payload(zone_b.id))
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_code_unique_refuse(self, client_admin_a, zone_a, depot_a):
        res = client_admin_a.post(DEPOTS_URL, self.get_payload(zone_a.id, code=depot_a.code))
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_nom_unique_par_zone_refuse(self, client_admin_a, zone_a, depot_a):
        res = client_admin_a.post(DEPOTS_URL, self.get_payload(zone_a.id, name=depot_a.name, code="NEWCODE"))
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_superviseur_refuse(self, client_superviseur_a, zone_a):
        res = client_superviseur_a.post(DEPOTS_URL, self.get_payload(zone_a.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_code_mis_en_majuscules(self, client_admin_a, zone_a):
        res = client_admin_a.post(DEPOTS_URL, self.get_payload(zone_a.id, code="minuscule"))
        assert res.status_code == status.HTTP_201_CREATED
        assert Depot.objects.get(id=res.data["id"]).code == "MINUSCULE"


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/depots/{id}/ — Modification
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDepotUpdate:

    def test_admin_modifie_depot(self, client_admin_a, depot_a):
        res = client_admin_a.patch(depot_url(depot_a.id), {"address": "Nouvelle adresse"})
        assert res.status_code == status.HTTP_200_OK
        depot_a.refresh_from_db()
        assert depot_a.address == "Nouvelle adresse"

    def test_admin_refuse_depot_autre_company(self, client_admin_a, depot_b):
        res = client_admin_a.patch(depot_url(depot_b.id), {"address": "Hack"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_deplacement_vers_zone_autre_company_refuse(self, client_admin_a, depot_a, zone_b):
        res = client_admin_a.patch(depot_url(depot_a.id), {"zone_id": zone_b.id})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_superviseur_refuse(self, client_superviseur_a, depot_a):
        res = client_superviseur_a.patch(depot_url(depot_a.id), {"address": "Hack"})
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/depots/{id}/ — Désactivation soft
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDepotDestroy:

    def test_admin_desactive_depot(self, client_admin_a, depot_a):
        res = client_admin_a.delete(depot_url(depot_a.id))
        assert res.status_code == status.HTTP_200_OK
        depot_a.refresh_from_db()
        assert depot_a.is_active is False

    def test_suppression_physique_impossible(self, client_admin_a, depot_a):
        client_admin_a.delete(depot_url(depot_a.id))
        assert Depot.objects.filter(id=depot_a.id).exists()

    def test_admin_refuse_depot_autre_company(self, client_admin_a, depot_b):
        res = client_admin_a.delete(depot_url(depot_b.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_superviseur_refuse(self, client_superviseur_a, depot_a):
        res = client_superviseur_a.delete(depot_url(depot_a.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/depots/{id}/dashboard/ — Placeholder
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDepotDashboard:

    def test_dashboard_retourne_objet_vide(self, client_admin_a, depot_a):
        res = client_admin_a.get(depot_dashboard_url(depot_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res.data == {}

    def test_dashboard_refuse_autre_company(self, client_admin_a, depot_b):
        res = client_admin_a.get(depot_dashboard_url(depot_b.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_dashboard_superviseur_autorise(self, client_superviseur_a, depot_a):
        res = client_superviseur_a.get(depot_dashboard_url(depot_a.id))
        assert res.status_code == status.HTTP_200_OK

    def test_dashboard_commercial_refuse(self, client_commercial_a, depot_a):
        res = client_commercial_a.get(depot_dashboard_url(depot_a.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN
