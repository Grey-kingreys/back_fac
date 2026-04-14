"""
apps/accounts/tests/conftest.py
Fixtures pytest partagées pour R1-B06, R1-B07, R1-B08.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser, Role
from apps.companies.models import Company, Depot, Zone

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_user(email, role, company=None, depot=None, is_active=True, password="Pass1234!"):
    return CustomUser.objects.create_user(
        email=email,
        password=password,
        first_name="Test",
        last_name="User",
        role=role,
        company=company,
        depot=depot,
        is_active=is_active,
    )


def auth_client(user, password="Pass1234!"):
    client = APIClient()
    res = client.post("/api/auth/login/", {"email": user.email, "password": password})
    assert res.status_code == 200, f"Login échoué pour {user.email} : {res.data}"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


# ─────────────────────────────────────────────────────────────────────────────
# Companies
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def company_a(db):
    return Company.objects.create(name="Company A", slug="company-a")


@pytest.fixture
def company_b(db):
    return Company.objects.create(name="Company B", slug="company-b")


# ─────────────────────────────────────────────────────────────────────────────
# Zones
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def zone_a(db, company_a):
    return Zone.objects.create(company=company_a, name="Zone Alpha", code="ZA")


@pytest.fixture
def zone_b(db, company_b):
    return Zone.objects.create(company=company_b, name="Zone Beta", code="ZB")


@pytest.fixture
def zone_a2(db, company_a):
    """Deuxième zone de company_a pour tester les listes."""
    return Zone.objects.create(company=company_a, name="Zone Alpha 2", code="ZA2")


# ─────────────────────────────────────────────────────────────────────────────
# Dépôts
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def depot_a(db, zone_a):
    return Depot.objects.create(zone=zone_a, name="Dépôt Central A", code="DCA")


@pytest.fixture
def depot_b(db, zone_b):
    return Depot.objects.create(zone=zone_b, name="Dépôt Central B", code="DCB")


@pytest.fixture
def depot_a2(db, zone_a):
    """Deuxième dépôt de company_a."""
    return Depot.objects.create(zone=zone_a, name="Dépôt Secondaire A", code="DSA")


# ─────────────────────────────────────────────────────────────────────────────
# Utilisateurs
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def superadmin(db):
    return make_user("superadmin@test.com", Role.SUPERADMIN)


@pytest.fixture
def admin_a(db, company_a):
    return make_user("admin_a@test.com", Role.ADMIN, company=company_a)


@pytest.fixture
def admin_b(db, company_b):
    return make_user("admin_b@test.com", Role.ADMIN, company=company_b)


@pytest.fixture
def superviseur_a(db, company_a):
    return make_user("superviseur_a@test.com", Role.SUPERVISEUR, company=company_a)


@pytest.fixture
def commercial_a(db, company_a):
    return make_user("commercial_a@test.com", Role.COMMERCIAL, company=company_a)


@pytest.fixture
def commercial_b(db, company_b):
    return make_user("commercial_b@test.com", Role.COMMERCIAL, company=company_b)


# ─────────────────────────────────────────────────────────────────────────────
# Clients API authentifiés
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client_superadmin(superadmin):
    return auth_client(superadmin)


@pytest.fixture
def client_admin_a(admin_a):
    return auth_client(admin_a)


@pytest.fixture
def client_admin_b(admin_b):
    return auth_client(admin_b)


@pytest.fixture
def client_superviseur_a(superviseur_a):
    return auth_client(superviseur_a)


@pytest.fixture
def client_commercial_a(commercial_a):
    return auth_client(commercial_a)


@pytest.fixture
def anon_client():
    return APIClient()
