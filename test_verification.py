#!/usr/bin/env python
"""
Test simple pour vérifier que les permissions fonctionnent correctement
"""

import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.accounts.models import CustomUser, Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole, IsCompanyMember
from apps.companies.models import Company, Zone


def test_simple():
    print("=== TEST SIMPLE DE VÉRIFICATION ===")

    # Créer deux companies
    company1 = Company.objects.create(name="Entreprise Test 1")
    company2 = Company.objects.create(name="Entreprise Test 2")

    # Créer des zones
    zone1 = Zone.objects.create(company=company1, name="Zone Test 1", code="ZT1")
    zone2 = Zone.objects.create(company=company2, name="Zone Test 2", code="ZT2")

    # Créer des utilisateurs
    user1 = CustomUser.objects.create_user(
        email="user1@test.com",
        first_name="User",
        last_name="One",
        password="test123",
        company=company1,
        role=Role.COMMERCIAL
    )

    user2 = CustomUser.objects.create_user(
        email="user2@test.com",
        first_name="User",
        last_name="Two",
        password="test123",
        company=company2,
        role=Role.COMMERCIAL
    )

    admin1 = CustomUser.objects.create_user(
        email="admin1@test.com",
        first_name="Admin",
        last_name="One",
        password="test123",
        company=company1,
        role=Role.ADMIN
    )

    superadmin = CustomUser.objects.create_user(
        email="superadmin@test.com",
        first_name="Super",
        last_name="Admin",
        password="test123",
        role=Role.SUPERADMIN
    )

    factory = APIRequestFactory()

    # Test 1: Isolation entre companies
    print("\n1. TEST ISOLATION ENTRE COMPANIES")

    permission = IsCompanyMember()

    # User1 peut voir sa zone
    request1 = factory.get('/')
    request1.user = user1
    can_see_own = permission.has_object_permission(request1, None, zone1)
    print(f"   User1 peut voir Zone1 (sa zone): {can_see_own} - {'OK' if can_see_own else 'ERREUR'}")

    # User1 ne peut PAS voir la zone de l'autre company
    cannot_see_other = permission.has_object_permission(request1, None, zone2)
    print(f"   User1 peut voir Zone2 (autre company): {cannot_see_other} - {'OK' if not cannot_see_other else 'ERREUR'}")

    # Test 2: Permissions par rôle
    print("\n2. TEST PERMISSIONS PAR RÔLE")

    role_permission = HasRole([Role.ADMIN, Role.SUPERADMIN])

    # Commercial n'a pas accès admin
    request_commercial = factory.get('/')
    request_commercial.user = user1
    commercial_access = role_permission.has_permission(request_commercial, None)
    print(f"   Commercial a accès admin: {commercial_access} - {'OK' if not commercial_access else 'ERREUR'}")

    # Admin a accès admin
    request_admin = factory.get('/')
    request_admin.user = admin1
    admin_access = role_permission.has_permission(request_admin, None)
    print(f"   Admin a accès admin: {admin_access} - {'OK' if admin_access else 'ERREUR'}")

    # Superadmin a accès admin
    request_super = factory.get('/')
    request_super.user = superadmin
    super_access = role_permission.has_permission(request_super, None)
    print(f"   Superadmin a accès admin: {super_access} - {'OK' if super_access else 'ERREUR'}")

    # Test 3: Filtrage automatique par company
    print("\n3. TEST FILTRAGE AUTOMATIQUE PAR COMPANY")

    class TestViewSet(CompanyFilterMixin, APIView):
        def __init__(self, queryset):
            self.queryset = queryset

    # User1 ne voit que les zones de sa company
    request1.user = user1
    view1 = TestViewSet(Zone.objects.all())
    view1.request = request1
    zones_user1 = view1.get_queryset()
    print(f"   User1 voit {zones_user1.count()} zones (attendu: 1) - {'OK' if zones_user1.count() == 1 else 'ERREUR'}")

    # Superadmin voit toutes les zones
    request_super.user = superadmin
    view_super = TestViewSet(Zone.objects.all())
    view_super.request = request_super
    zones_super = view_super.get_queryset()
    print(f"   Superadmin voit {zones_super.count()} zones (attendu: 2) - {'OK' if zones_super.count() == 2 else 'ERREUR'}")

    # Test 4: Vérification finale
    print("\n4. VÉRIFICATION FINALE")

    all_ok = True

    if not can_see_own:
        print("   ERREUR: User1 devrait voir sa propre zone")
        all_ok = False

    if cannot_see_other:
        print("   ERREUR: User1 ne devrait PAS voir la zone de l'autre company")
        all_ok = False

    if commercial_access:
        print("   ERREUR: Commercial ne devrait PAS avoir accès admin")
        all_ok = False

    if not admin_access:
        print("   ERREUR: Admin devrait avoir accès admin")
        all_ok = False

    if not super_access:
        print("   ERREUR: Superadmin devrait avoir accès admin")
        all_ok = False

    if zones_user1.count() != 1:
        print("   ERREUR: User1 devrait voir uniquement 1 zone")
        all_ok = False

    if zones_super.count() != 2:
        print("   ERREUR: Superadmin devrait voir toutes les zones")
        all_ok = False

    if all_ok:
        print("\n   === TOUS LES TESTS RÉUSSIS ===")
        print("   L'isolation multi-companies fonctionne parfaitement!")
        print("   Les permissions par rôle fonctionnent!")
        print("   Le filtrage automatique fonctionne!")
        return True
    else:
        print("\n   === CERTAINS TESTS ONT ÉCHOUÉ ===")
        return False

if __name__ == "__main__":
    test_simple()
