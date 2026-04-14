"""
apps/accounts/tests/test_permissions.py
R1-B06 — Tests complets des permissions et isolation multi-companies.
Lancer : pytest apps/accounts/tests/test_permissions.py -v
"""

from django.test import RequestFactory

import pytest

from apps.accounts.models import CustomUser, Role
from apps.accounts.permissions import (
    CompanyFilterMixin,
    HasRole,
    IsAdminOrSuperAdmin,
    IsCompanyMember,
    IsSupervisorOrAbove,
)
from apps.companies.models import Company, Depot, Zone

# ─────────────────────────────────────────────────────────────────────────────
# Helpers locaux
# ─────────────────────────────────────────────────────────────────────────────


class FakeViewSet:
    """Simule un ViewSet pour les mixins qui ont besoin de self.request."""
    def __init__(self, queryset, request):
        self.queryset = queryset
        self.request = request


def make_request(user):
    factory = RequestFactory()
    req = factory.get("/")
    req.user = user
    return req


# ─────────────────────────────────────────────────────────────────────────────
# IsCompanyMember
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIsCompanyMember:

    def test_user_acces_propre_company(self, admin_a, zone_a):
        perm = IsCompanyMember()
        req = make_request(admin_a)
        assert perm.has_object_permission(req, None, zone_a) is True

    def test_user_refuse_autre_company(self, admin_a, zone_b):
        perm = IsCompanyMember()
        req = make_request(admin_a)
        assert perm.has_object_permission(req, None, zone_b) is False

    def test_superadmin_acces_toutes_companies(self, superadmin, zone_a, zone_b):
        perm = IsCompanyMember()
        req = make_request(superadmin)
        assert perm.has_object_permission(req, None, zone_a) is True
        assert perm.has_object_permission(req, None, zone_b) is True

    def test_user_sans_company_refuse(self, db):
        user = CustomUser.objects.create_user(
            email="nocompany@test.com",
            password="Pass1234!",
            first_name="No",
            last_name="Company",
            role=Role.COMMERCIAL,
        )
        perm = IsCompanyMember()
        req = make_request(user)
        assert perm.has_object_permission(req, None, Zone(company=None)) is False

    def test_acces_depot_via_property_company(self, admin_a, depot_a, depot_b):
        """Depot.company est une @property — IsCompanyMember doit quand même fonctionner."""
        perm = IsCompanyMember()
        req = make_request(admin_a)
        assert perm.has_object_permission(req, None, depot_a) is True
        assert perm.has_object_permission(req, None, depot_b) is False


# ─────────────────────────────────────────────────────────────────────────────
# HasRole
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestHasRole:

    def test_role_autorise(self, superviseur_a):
        perm = HasRole([Role.ADMIN, Role.SUPERVISEUR])
        req = make_request(superviseur_a)
        assert perm.has_permission(req, None) is True

    def test_role_refuse(self, commercial_a):
        perm = HasRole([Role.ADMIN, Role.SUPERVISEUR])
        req = make_request(commercial_a)
        assert perm.has_permission(req, None) is False

    def test_superadmin_bypass_tous_roles(self, superadmin):
        perm = HasRole([Role.ADMIN])
        req = make_request(superadmin)
        assert perm.has_permission(req, None) is True

    def test_liste_vide_autorise_tous_authentifies(self, commercial_a):
        perm = HasRole([])
        req = make_request(commercial_a)
        assert perm.has_permission(req, None) is True

    def test_user_non_authentifie_refuse(self):
        perm = HasRole([Role.ADMIN])
        req = make_request(None)
        assert perm.has_permission(req, None) is False


# ─────────────────────────────────────────────────────────────────────────────
# CompanyFilterMixin
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCompanyFilterMixin:

    def test_user_voit_seulement_sa_company(self, admin_a, zone_a, zone_b):
        req = make_request(admin_a)
        # view = FakeViewSet(Zone.objects.all(), req)
        mixin = CompanyFilterMixin()
        mixin.request = req
        mixin.queryset = Zone.objects.all()
        qs = mixin.get_queryset()
        assert zone_a in qs
        assert zone_b not in qs

    def test_superadmin_voit_tout(self, superadmin, zone_a, zone_b):
        req = make_request(superadmin)
        mixin = CompanyFilterMixin()
        mixin.request = req
        mixin.queryset = Zone.objects.all()
        qs = mixin.get_queryset()
        assert zone_a in qs
        assert zone_b in qs

    def test_user_sans_company_voit_rien(self, db, zone_a, zone_b):
        user = CustomUser.objects.create_user(
            email="nocompany2@test.com",
            password="Pass1234!",
            first_name="No",
            last_name="Company",
            role=Role.COMMERCIAL,
        )
        req = make_request(user)
        mixin = CompanyFilterMixin()
        mixin.request = req
        mixin.queryset = Zone.objects.all()
        qs = mixin.get_queryset()
        assert qs.count() == 0

    def test_isolation_complete_deux_companies(self, admin_a, admin_b, zone_a, zone_b, depot_a, depot_b):
        """Un admin A ne voit pas les données de B et vice-versa."""
        for user, visible, invisible in [
            (admin_a, zone_a, zone_b),
            (admin_b, zone_b, zone_a),
        ]:
            req = make_request(user)
            mixin = CompanyFilterMixin()
            mixin.request = req
            mixin.queryset = Zone.objects.all()
            qs = mixin.get_queryset()
            assert visible in qs
            assert invisible not in qs


# ─────────────────────────────────────────────────────────────────────────────
# Permissions composées
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPermissionsComposees:

    def test_is_admin_or_superadmin(self, admin_a, superviseur_a, commercial_a, superadmin):
        perm = IsAdminOrSuperAdmin()
        assert perm.has_permission(make_request(admin_a), None) is True
        assert perm.has_permission(make_request(superadmin), None) is True
        assert perm.has_permission(make_request(superviseur_a), None) is False
        assert perm.has_permission(make_request(commercial_a), None) is False

    def test_is_supervisor_or_above(self, admin_a, superviseur_a, commercial_a, superadmin):
        perm = IsSupervisorOrAbove()
        assert perm.has_permission(make_request(superviseur_a), None) is True
        assert perm.has_permission(make_request(admin_a), None) is True
        assert perm.has_permission(make_request(superadmin), None) is True
        assert perm.has_permission(make_request(commercial_a), None) is False
