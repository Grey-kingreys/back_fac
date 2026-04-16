"""
apps/accounts/tests/test_users.py
R1-B07 — Tests complets CRUD Utilisateurs.
Lancer : pytest apps/accounts/tests/test_users.py -v
"""

import pytest
from rest_framework import status

from apps.accounts.models import CustomUser, Role

USERS_URL = "/api/users/"


def detail_url(pk):
    return f"/api/users/{pk}/"


def reset_url(pk):
    return f"/api/users/{pk}/reset-password/"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/users/ — Liste
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserList:

    def test_admin_voit_users_de_sa_company(self, client_admin_a, admin_a, commercial_a, commercial_b):
        res = client_admin_a.get(USERS_URL)
        assert res.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in res.data["results"]]
        assert admin_a.email in emails
        assert commercial_a.email in emails
        assert commercial_b.email not in emails  # autre company

    def test_superviseur_peut_lister(self, client_superviseur_a, commercial_a):
        res = client_superviseur_a.get(USERS_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_commercial_refuse(self, client_commercial_a):
        res = client_commercial_a.get(USERS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(USERS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filtre_par_role(self, client_admin_a, admin_a, commercial_a):
        res = client_admin_a.get(USERS_URL, {"role": Role.COMMERCIAL})
        assert res.status_code == status.HTTP_200_OK
        roles = [u["role"] for u in res.data["results"]]
        assert all(r == Role.COMMERCIAL for r in roles)

    def test_filtre_par_is_active(self, client_admin_a, company_a):
        from apps.accounts.tests.conftest import make_user
        inactive = make_user("inactive@a.com", Role.COMMERCIAL, company=company_a, is_active=False)
        res = client_admin_a.get(USERS_URL, {"is_active": "false"})
        assert res.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in res.data["results"]]
        assert inactive.email in emails

    def test_filtre_par_depot(self, client_admin_a, company_a, depot_a, depot_a2):
        from apps.accounts.tests.conftest import make_user
        user_with_depot = make_user("depotuser@a.com", Role.CAISSIER, company=company_a, depot=depot_a)
        res = client_admin_a.get(USERS_URL, {"depot": depot_a.id})
        assert res.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in res.data["results"]]
        assert user_with_depot.email in emails

    def test_superadmin_voit_toutes_companies(self, client_superadmin, commercial_a, commercial_b):
        res = client_superadmin.get(USERS_URL)
        assert res.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in res.data["results"]]
        assert commercial_a.email in emails
        assert commercial_b.email in emails


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/users/{id}/ — Détail
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserDetail:

    def test_admin_voit_user_de_sa_company(self, client_admin_a, commercial_a):
        res = client_admin_a.get(detail_url(commercial_a.id))
        assert res.status_code == status.HTTP_200_OK
        assert res.data["email"] == commercial_a.email

    def test_admin_refuse_user_autre_company(self, client_admin_a, commercial_b):
        res = client_admin_a.get(detail_url(commercial_b.id))
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_superviseur_voit_user_sa_company(self, client_superviseur_a, commercial_a):
        res = client_superviseur_a.get(detail_url(commercial_a.id))
        assert res.status_code == status.HTTP_200_OK

    def test_commercial_refuse(self, client_commercial_a, admin_a):
        res = client_commercial_a.get(detail_url(admin_a.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_404_user_inexistant(self, client_admin_a):
        res = client_admin_a.get(detail_url(99999))
        assert res.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/users/ — Création
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserCreate:

    def get_payload(self, **kwargs):
        data = {
            "email": "nouveau@test.com",
            "first_name": "Nouveau",
            "last_name": "User",
            "phone": "+224 620 000 099",
            "role": Role.COMMERCIAL,
            "password": "SecurePass123!",
        }
        data.update(kwargs)
        return data

    def test_admin_cree_user(self, client_admin_a, company_a):
        res = client_admin_a.post(USERS_URL, self.get_payload())
        assert res.status_code == status.HTTP_201_CREATED
        assert CustomUser.objects.filter(email="nouveau@test.com").exists()
        # Vérifie que l'user est bien rattaché à la company de l'admin
        user = CustomUser.objects.get(email="nouveau@test.com")
        assert user.company == company_a

    def test_superviseur_refuse_creation(self, client_superviseur_a):
        res = client_superviseur_a.post(USERS_URL, self.get_payload())
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_commercial_refuse_creation(self, client_commercial_a):
        res = client_commercial_a.post(USERS_URL, self.get_payload())
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.post(USERS_URL, self.get_payload())
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_email_unique_par_company(self, client_admin_a, commercial_a):
        """On ne peut pas créer un second user avec le même email dans la même company."""
        res = client_admin_a.post(USERS_URL, self.get_payload(email=commercial_a.email))
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in res.data

    def test_email_invalide_refuse(self, client_admin_a):
        res = client_admin_a.post(USERS_URL, self.get_payload(email="pasunemail"))
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_role_invalide_refuse(self, client_admin_a):
        res = client_admin_a.post(USERS_URL, self.get_payload(role="role_inexistant"))
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_trop_court_refuse(self, client_admin_a):
        res = client_admin_a.post(USERS_URL, self.get_payload(password="123"))
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_depot_autre_company_refuse(self, client_admin_a, depot_b):
        """Le dépôt doit appartenir à la company de l'admin créateur."""
        res = client_admin_a.post(USERS_URL, self.get_payload(depot_id=depot_b.id))
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_depot_meme_company_accepte(self, client_admin_a, depot_a):
        res = client_admin_a.post(USERS_URL, self.get_payload(depot_id=depot_a.id))
        assert res.status_code == status.HTTP_201_CREATED
        user = CustomUser.objects.get(email="nouveau@test.com")
        assert user.depot == depot_a

    def test_champs_obligatoires_manquants(self, client_admin_a):
        res = client_admin_a.post(USERS_URL, {"email": "incomplet@test.com"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/users/{id}/ — Modification
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserUpdate:

    def test_admin_modifie_user_sa_company(self, client_admin_a, commercial_a):
        res = client_admin_a.patch(detail_url(commercial_a.id), {"first_name": "Modifié"})
        assert res.status_code == status.HTTP_200_OK
        commercial_a.refresh_from_db()
        assert commercial_a.first_name == "Modifié"

    def test_admin_refuse_user_autre_company(self, client_admin_a, commercial_b):
        res = client_admin_a.patch(detail_url(commercial_b.id), {"first_name": "Hack"})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_superviseur_refuse_modification(self, client_superviseur_a, commercial_a):
        res = client_superviseur_a.patch(detail_url(commercial_a.id), {"first_name": "Hack"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_changement_role_valide(self, client_admin_a, commercial_a):
        res = client_admin_a.patch(detail_url(commercial_a.id), {"role": Role.CAISSIER})
        assert res.status_code == status.HTTP_200_OK
        commercial_a.refresh_from_db()
        assert commercial_a.role == Role.CAISSIER

    def test_depot_autre_company_refuse(self, client_admin_a, commercial_a, depot_b):
        res = client_admin_a.patch(detail_url(commercial_a.id), {"depot_id": depot_b.id})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_depot_meme_company_accepte(self, client_admin_a, commercial_a, depot_a):
        res = client_admin_a.patch(detail_url(commercial_a.id), {"depot_id": depot_a.id})
        assert res.status_code == status.HTTP_200_OK
        commercial_a.refresh_from_db()
        assert commercial_a.depot == depot_a


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/users/{id}/ — Désactivation soft
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserDestroy:

    def test_admin_desactive_user_sa_company(self, client_admin_a, commercial_a):
        res = client_admin_a.delete(detail_url(commercial_a.id))
        assert res.status_code == status.HTTP_200_OK
        commercial_a.refresh_from_db()
        assert commercial_a.is_active is False

    def test_suppression_physique_impossible(self, client_admin_a, commercial_a):
        """Le DELETE ne supprime pas l'enregistrement, il désactive seulement."""
        client_admin_a.delete(detail_url(commercial_a.id))
        assert CustomUser.objects.filter(id=commercial_a.id).exists()

    def test_admin_refuse_autre_company(self, client_admin_a, commercial_b):
        res = client_admin_a.delete(detail_url(commercial_b.id))
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_ne_peut_pas_se_desactiver(self, client_admin_a, admin_a):
        res = client_admin_a.delete(detail_url(admin_a.id))
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        admin_a.refresh_from_db()
        assert admin_a.is_active is True

    def test_superviseur_refuse(self, client_superviseur_a, commercial_a):
        res = client_superviseur_a.delete(detail_url(commercial_a.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/users/{id}/reset-password/ — Reset mot de passe
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserResetPassword:

    def test_admin_reset_password_user_sa_company(self, client_admin_a, commercial_a):
        res = client_admin_a.post(reset_url(commercial_a.id), {
            "new_password": "NouveauPass123!",
            "new_password_confirm": "NouveauPass123!",
        })
        assert res.status_code == status.HTTP_200_OK
        commercial_a.refresh_from_db()
        assert commercial_a.check_password("NouveauPass123!")

    def test_reset_reactive_compte_bloque(self, client_admin_a, company_a):
        from apps.accounts.tests.conftest import make_user
        locked = make_user("locked@a.com", Role.COMMERCIAL, company=company_a, is_active=False)
        locked.failed_attempts = 5
        locked.save()
        res = client_admin_a.post(reset_url(locked.id), {
            "new_password": "NouveauPass123!",
            "new_password_confirm": "NouveauPass123!",
        })
        assert res.status_code == status.HTTP_200_OK
        locked.refresh_from_db()
        assert locked.is_active is True
        assert locked.failed_attempts == 0

    def test_passwords_differents_refuses(self, client_admin_a, commercial_a):
        res = client_admin_a.post(reset_url(commercial_a.id), {
            "new_password": "NouveauPass123!",
            "new_password_confirm": "AutrePass456!",
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_trop_faible_refuse(self, client_admin_a, commercial_a):
        res = client_admin_a.post(reset_url(commercial_a.id), {
            "new_password": "123",
            "new_password_confirm": "123",
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_refuse_autre_company(self, client_admin_a, commercial_b):
        res = client_admin_a.post(reset_url(commercial_b.id), {
            "new_password": "NouveauPass123!",
            "new_password_confirm": "NouveauPass123!",
        })
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_superviseur_refuse(self, client_superviseur_a, commercial_a):
        res = client_superviseur_a.post(reset_url(commercial_a.id), {
            "new_password": "NouveauPass123!",
            "new_password_confirm": "NouveauPass123!",
        })
        assert res.status_code == status.HTTP_403_FORBIDDEN
