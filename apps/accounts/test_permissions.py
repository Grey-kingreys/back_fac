"""
apps/accounts/test_permissions.py
Tests unitaires pour les permissions et l'isolation multi-companies.
"""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

import pytest
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.companies.models import Company, Depot, Zone

from .models import Role
from .permissions import (
    CompanyFilterMixin,
    HasRole,
    IsAdminOrSuperAdmin,
    IsCompanyMember,
    IsCompanyMemberOrReadOnly,
    IsOwnerOrCompanyAdmin,
    IsSupervisorOrAbove,
)

User = get_user_model()


class TestCompanyModel:
    """Modèle de test pour simuler des objets avec company."""

    def __init__(self, company):
        self.company = company
        self.id = 1


class TestUserModel:
    """Modèle de test pour simuler des objets avec user."""

    def __init__(self, user):
        self.user = user
        self.id = user.id


class TestCompanyFilterViewSet(CompanyFilterMixin, APIView):
    """ViewSet de test pour le mixin CompanyFilterMixin."""

    def __init__(self, queryset):
        self.queryset = queryset
        super().__init__()


class IsCompanyMemberTest(TestCase):
    """Tests pour la permission IsCompanyMember."""

    def setUp(self):
        self.factory = RequestFactory()
        self.permission = IsCompanyMember()

        # Créer deux companies
        self.company_a = Company.objects.create(name="Company A")
        self.company_b = Company.objects.create(name="Company B")

        # Créer des utilisateurs pour chaque company
        self.user_a = User.objects.create_user(
            email="user_a@test.com",
            first_name="User",
            last_name="A",
            password="test123",
            company=self.company_a,
            role=Role.COMMERCIAL
        )

        self.user_b = User.objects.create_user(
            email="user_b@test.com",
            first_name="User",
            last_name="B",
            password="test123",
            company=self.company_b,
            role=Role.COMMERCIAL
        )

        # Créer un superadmin
        self.superadmin = User.objects.create_user(
            email="superadmin@test.com",
            first_name="Super",
            last_name="Admin",
            password="test123",
            role=Role.SUPERADMIN
        )

        # Objets de test
        self.obj_company_a = TestCompanyModel(self.company_a)
        self.obj_company_b = TestCompanyModel(self.company_b)

    def test_user_can_access_own_company_object(self):
        """Un utilisateur peut accéder aux objets de sa company."""
        request = self.factory.get('/')
        request.user = self.user_a

        result = self.permission.has_object_permission(request, None, self.obj_company_a)
        self.assertTrue(result)

    def test_user_cannot_access_other_company_object(self):
        """Un utilisateur ne peut pas accéder aux objets d'une autre company."""
        request = self.factory.get('/')
        request.user = self.user_a

        result = self.permission.has_object_permission(request, None, self.obj_company_b)
        self.assertFalse(result)

    def test_superadmin_can_access_any_company_object(self):
        """Le superadmin peut accéder à n'importe quel objet."""
        request = self.factory.get('/')
        request.user = self.superadmin

        result = self.permission.has_object_permission(request, None, self.obj_company_a)
        self.assertTrue(result)

        result = self.permission.has_object_permission(request, None, self.obj_company_b)
        self.assertTrue(result)

    def test_user_without_company_cannot_access(self):
        """Un utilisateur sans company ne peut rien accéder."""
        user_no_company = User.objects.create_user(
            email="no_company@test.com",
            first_name="No",
            last_name="Company",
            password="test123",
            role=Role.COMMERCIAL
        )

        request = self.factory.get('/')
        request.user = user_no_company

        result = self.permission.has_object_permission(request, None, self.obj_company_a)
        self.assertFalse(result)


class HasRoleTest(TestCase):
    """Tests pour la permission HasRole."""

    def setUp(self):
        self.factory = RequestFactory()
        self.company = Company.objects.create(name="Test Company")

        # Créer des utilisateurs avec différents rôles
        self.commercial = User.objects.create_user(
            email="commercial@test.com",
            first_name="Commercial",
            last_name="User",
            password="test123",
            company=self.company,
            role=Role.COMMERCIAL
        )

        self.superviseur = User.objects.create_user(
            email="superviseur@test.com",
            first_name="Superviseur",
            last_name="User",
            password="test123",
            company=self.company,
            role=Role.SUPERVISEUR
        )

        self.admin = User.objects.create_user(
            email="admin@test.com",
            first_name="Admin",
            last_name="User",
            password="test123",
            company=self.company,
            role=Role.ADMIN
        )

        self.superadmin = User.objects.create_user(
            email="superadmin@test.com",
            first_name="Super",
            last_name="Admin",
            password="test123",
            role=Role.SUPERADMIN
        )

    def test_user_with_allowed_role_can_access(self):
        """Un utilisateur avec un rôle autorisé peut accéder."""
        permission = HasRole([Role.ADMIN, Role.SUPERVISEUR])
        request = self.factory.get('/')
        request.user = self.superviseur

        result = permission.has_permission(request, None)
        self.assertTrue(result)

    def test_user_with_disallowed_role_cannot_access(self):
        """Un utilisateur avec un rôle non autorisé ne peut pas accéder."""
        permission = HasRole([Role.ADMIN, Role.SUPERVISEUR])
        request = self.factory.get('/')
        request.user = self.commercial

        result = permission.has_permission(request, None)
        self.assertFalse(result)

    def test_superadmin_can_access_any_role(self):
        """Le superadmin peut accéder même si son rôle n'est pas dans la liste."""
        permission = HasRole([Role.ADMIN, Role.SUPERVISEUR])
        request = self.factory.get('/')
        request.user = self.superadmin

        result = permission.has_permission(request, None)
        self.assertTrue(result)

    def test_unauthenticated_user_cannot_access(self):
        """Un utilisateur non authentifié ne peut pas accéder."""
        permission = HasRole([Role.ADMIN])
        request = self.factory.get('/')
        request.user = None

        result = permission.has_permission(request, None)
        self.assertFalse(result)

    def test_no_roles_allowed_means_all_authenticated_users(self):
        """Si aucun rôle n'est spécifié, tous les utilisateurs authentifiés peuvent accéder."""
        permission = HasRole()
        request = self.factory.get('/')
        request.user = self.commercial

        result = permission.has_permission(request, None)
        self.assertTrue(result)


class CompanyFilterMixinTest(TestCase):
    """Tests pour le mixin CompanyFilterMixin."""

    def setUp(self):
        self.factory = RequestFactory()

        # Créer deux companies
        self.company_a = Company.objects.create(name="Company A")
        self.company_b = Company.objects.create(name="Company B")

        # Créer des utilisateurs
        self.user_a = User.objects.create_user(
            email="user_a@test.com",
            first_name="User",
            last_name="A",
            password="test123",
            company=self.company_a,
            role=Role.COMMERCIAL
        )

        self.user_b = User.objects.create_user(
            email="user_b@test.com",
            first_name="User",
            last_name="B",
            password="test123",
            company=self.company_b,
            role=Role.COMMERCIAL
        )

        self.superadmin = User.objects.create_user(
            email="superadmin@test.com",
            first_name="Super",
            last_name="Admin",
            password="test123",
            role=Role.SUPERADMIN
        )

        # Créer des zones pour chaque company
        self.zone_a = Zone.objects.create(company=self.company_a, name="Zone A", code="ZA")
        self.zone_b = Zone.objects.create(company=self.company_b, name="Zone B", code="ZB")

    def test_user_sees_only_his_company_data(self):
        """Un utilisateur ne voit que les données de sa company."""
        request = self.factory.get('/')
        request.user = self.user_a

        view = TestCompanyFilterViewSet(Zone.objects.all())
        view.request = request

        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.zone_a)

    def test_superadmin_sees_all_data(self):
        """Le superadmin voit toutes les données."""
        request = self.factory.get('/')
        request.user = self.superadmin

        view = TestCompanyFilterViewSet(Zone.objects.all())
        view.request = request

        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), 2)

    def test_user_without_company_sees_nothing(self):
        """Un utilisateur sans company ne voit rien."""
        user_no_company = User.objects.create_user(
            email="no_company@test.com",
            first_name="No",
            last_name="Company",
            password="test123",
            role=Role.COMMERCIAL
        )

        request = self.factory.get('/')
        request.user = user_no_company

        view = TestCompanyFilterViewSet(Zone.objects.all())
        view.request = request

        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), 0)


class IsOwnerOrCompanyAdminTest(TestCase):
    """Tests pour la permission IsOwnerOrCompanyAdmin."""

    def setUp(self):
        self.factory = RequestFactory()
        self.company = Company.objects.create(name="Test Company")

        self.user = User.objects.create_user(
            email="user@test.com",
            first_name="User",
            last_name="Test",
            password="test123",
            company=self.company,
            role=Role.COMMERCIAL
        )

        self.admin = User.objects.create_user(
            email="admin@test.com",
            first_name="Admin",
            last_name="User",
            password="test123",
            company=self.company,
            role=Role.ADMIN
        )

        self.superadmin = User.objects.create_user(
            email="superadmin@test.com",
            first_name="Super",
            last_name="Admin",
            password="test123",
            role=Role.SUPERADMIN
        )

        # Objets de test
        self.user_obj = TestUserModel(self.user)
        self.user_obj.company = self.company

    def test_user_can_access_own_object(self):
        """Un utilisateur peut accéder à ses propres objets."""
        permission = IsOwnerOrCompanyAdmin()
        request = self.factory.get('/')
        request.user = self.user

        result = permission.has_object_permission(request, None, self.user_obj)
        self.assertTrue(result)

    def test_admin_can_access_company_user_object(self):
        """Un admin peut accéder aux objets des utilisateurs de sa company."""
        permission = IsOwnerOrCompanyAdmin()
        request = self.factory.get('/')
        request.user = self.admin

        result = permission.has_object_permission(request, None, self.user_obj)
        self.assertTrue(result)

    def test_superadmin_can_access_any_object(self):
        """Le superadmin peut accéder à n'importe quel objet."""
        permission = IsOwnerOrCompanyAdmin()
        request = self.factory.get('/')
        request.user = self.superadmin

        result = permission.has_object_permission(request, None, self.user_obj)
        self.assertTrue(result)


class IsolationIntegrationTest(TestCase):
    """Test d'intégration pour l'isolation complète entre companies."""

    def setUp(self):
        self.factory = RequestFactory()

        # Créer deux companies complètement isolées
        self.company_a = Company.objects.create(name="Company A")
        self.company_b = Company.objects.create(name="Company B")

        # Créer des zones et dépôts pour chaque company
        self.zone_a = Zone.objects.create(company=self.company_a, name="Zone A", code="ZA")
        self.zone_b = Zone.objects.create(company=self.company_b, name="Zone B", code="ZB")

        self.depot_a = Depot.objects.create(zone=self.zone_a, name="Depot A", code="DA")
        self.depot_b = Depot.objects.create(zone=self.zone_b, name="Depot B", code="DB")

        # Créer des utilisateurs pour chaque company
        self.user_a = User.objects.create_user(
            email="user_a@test.com",
            first_name="User",
            last_name="A",
            password="test123",
            company=self.company_a,
            depot=self.depot_a,
            role=Role.COMMERCIAL
        )

        self.user_b = User.objects.create_user(
            email="user_b@test.com",
            first_name="User",
            last_name="B",
            password="test123",
            company=self.company_b,
            depot=self.depot_b,
            role=Role.COMMERCIAL
        )

        self.admin_a = User.objects.create_user(
            email="admin_a@test.com",
            first_name="Admin",
            last_name="A",
            password="test123",
            company=self.company_a,
            role=Role.ADMIN
        )

    def test_complete_isolation_between_companies(self):
        """Test complet de l'isolation entre companies."""
        # Test 1: User A ne peut voir que les données de Company A
        request_a = self.factory.get('/')
        request_a.user = self.user_a

        view_zones_a = TestCompanyFilterViewSet(Zone.objects.all())
        view_zones_a.request = request_a
        zones_a = view_zones_a.get_queryset()

        view_depots_a = TestCompanyFilterViewSet(Depot.objects.all())
        view_depots_a.request = request_a
        depots_a = view_depots_a.get_queryset()

        self.assertEqual(zones_a.count(), 1)
        self.assertEqual(zones_a.first(), self.zone_a)
        self.assertEqual(depots_a.count(), 1)
        self.assertEqual(depots_a.first(), self.depot_a)

        # Test 2: User B ne peut voir que les données de Company B
        request_b = self.factory.get('/')
        request_b.user = self.user_b

        view_zones_b = TestCompanyFilterViewSet(Zone.objects.all())
        view_zones_b.request = request_b
        zones_b = view_zones_b.get_queryset()

        view_depots_b = TestCompanyFilterViewSet(Depot.objects.all())
        view_depots_b.request = request_b
        depots_b = view_depots_b.get_queryset()

        self.assertEqual(zones_b.count(), 1)
        self.assertEqual(zones_b.first(), self.zone_b)
        self.assertEqual(depots_b.count(), 1)
        self.assertEqual(depots_b.first(), self.depot_b)

        # Test 3: Admin A peut voir toutes les données de Company A
        request_admin_a = self.factory.get('/')
        request_admin_a.user = self.admin_a

        view_zones_admin_a = TestCompanyFilterViewSet(Zone.objects.all())
        view_zones_admin_a.request = request_admin_a
        zones_admin_a = view_zones_admin_a.get_queryset()

        view_depots_admin_a = TestCompanyFilterViewSet(Depot.objects.all())
        view_depots_admin_a.request = request_admin_a
        depots_admin_a = view_depots_admin_a.get_queryset()

        self.assertEqual(zones_admin_a.count(), 1)
        self.assertEqual(zones_admin_a.first(), self.zone_a)
        self.assertEqual(depots_admin_a.count(), 1)
        self.assertEqual(depots_admin_a.first(), self.depot_a)

        # Test 4: Permission IsCompanyMember empêche l'accès cross-company
        permission = IsCompanyMember()

        # User A essaie d'accéder à une zone de Company B
        result = permission.has_object_permission(request_a, None, self.zone_b)
        self.assertFalse(result)

        # User A peut accéder à sa propre zone
        result = permission.has_object_permission(request_a, None, self.zone_a)
        self.assertTrue(result)

        # Admin A peut accéder aux zones de sa company
        result = permission.has_object_permission(request_admin_a, None, self.zone_a)
        self.assertTrue(result)

        # Admin A ne peut pas accéder aux zones d'une autre company
        result = permission.has_object_permission(request_admin_a, None, self.zone_b)
        self.assertFalse(result)


@pytest.mark.django_db
class TestPermissionsWithPytest:
    """Tests pytest pour les permissions (alternative à TestCase)."""

    def test_is_admin_or_super_admin_permission(self):
        """Test la permission IsAdminOrSuperAdmin."""
        company = Company.objects.create(name="Test Company")

        commercial = User.objects.create_user(
            email="commercial@test.com",
            first_name="Commercial",
            last_name="User",
            password="test123",
            company=company,
            role=Role.COMMERCIAL
        )

        admin = User.objects.create_user(
            email="admin@test.com",
            first_name="Admin",
            last_name="User",
            password="test123",
            company=company,
            role=Role.ADMIN
        )

        superadmin = User.objects.create_user(
            email="superadmin@test.com",
            first_name="Super",
            last_name="Admin",
            password="test123",
            role=Role.SUPERADMIN
        )

        factory = RequestFactory()
        permission = IsAdminOrSuperAdmin()

        # Commercial n'a pas accès
        request = factory.get('/')
        request.user = commercial
        assert not permission.has_permission(request, None)

        # Admin a accès
        request.user = admin
        assert permission.has_permission(request, None)

        # Superadmin a accès
        request.user = superadmin
        assert permission.has_permission(request, None)

    def test_is_supervisor_or_above_permission(self):
        """Test la permission IsSupervisorOrAbove."""
        company = Company.objects.create(name="Test Company")

        commercial = User.objects.create_user(
            email="commercial@test.com",
            first_name="Commercial",
            last_name="User",
            password="test123",
            company=company,
            role=Role.COMMERCIAL
        )

        superviseur = User.objects.create_user(
            email="superviseur@test.com",
            first_name="Superviseur",
            last_name="User",
            password="test123",
            company=company,
            role=Role.SUPERVISEUR
        )

        factory = RequestFactory()
        permission = IsSupervisorOrAbove()

        # Commercial n'a pas accès
        request = factory.get('/')
        request.user = commercial
        assert not permission.has_permission(request, None)

        # Superviseur a accès
        request.user = superviseur
        assert permission.has_permission(request, None)
