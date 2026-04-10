#!/usr/bin/env python
"""
Test final des permissions - à exécuter avec: python manage.py shell < test_permissions_final.py
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.companies.models import Company, Zone
from apps.accounts.models import CustomUser, Role
from apps.accounts.permissions import IsOwnerOrCompanyAdmin, IsAdminOrSuperAdmin, IsSupervisorOrAbove, IsCompanyMember
from rest_framework.test import APIRequestFactory

def run_final_tests():
    """Test final d'intégration complète."""
    print('=== TEST FINAL D\'ISOLATION MULTI-COMPANIES ===')

    # Nettoyer et recréer les données
    CustomUser.objects.filter(email__contains='@final.com').delete()
    Company.objects.filter(name__contains='Final').delete()
    Zone.objects.all().delete()

    # Créer deux companies complètement isolées
    company_a = Company.objects.create(name='Final Company A')
    company_b = Company.objects.create(name='Final Company B')

    # Créer des zones pour chaque company
    zone_a = Zone.objects.create(company=company_a, name='Final Zone A', code='FZA')
    zone_b = Zone.objects.create(company=company_b, name='Final Zone B', code='FZB')

    # Créer des utilisateurs avec différents rôles
    user_a_commercial = CustomUser.objects.create_user(
        email='commercial_a@final.com',
        first_name='Commercial',
        last_name='A',
        password='test123',
        company=company_a,
        role=Role.COMMERCIAL
    )

    user_a_admin = CustomUser.objects.create_user(
        email='admin_a@final.com',
        first_name='Admin',
        last_name='A',
        password='test123',
        company=company_a,
        role=Role.ADMIN
    )

    user_b_commercial = CustomUser.objects.create_user(
        email='commercial_b@final.com',
        first_name='Commercial',
        last_name='B',
        password='test123',
        company=company_b,
        role=Role.COMMERCIAL
    )

    superadmin = CustomUser.objects.create_user(
        email='superadmin@final.com',
        first_name='Super',
        last_name='Admin',
        password='test123',
        role=Role.SUPERADMIN
    )

    factory = APIRequestFactory()

    # Test 1: Isolation par permission objet
    permission_company = IsCompanyMember()

    # User A commercial ne peut pas voir les données de Company B
    request_a = factory.get('/')
    request_a.user = user_a_commercial
    access_a_to_b = permission_company.has_object_permission(request_a, None, zone_b)
    print(f'User A commercial peut voir Zone B: {access_a_to_b} (FALSE attendu)')

    # User A commercial peut voir les données de Company A
    access_a_to_a = permission_company.has_object_permission(request_a, None, zone_a)
    print(f'User A commercial peut voir Zone A: {access_a_to_a} (TRUE attendu)')

    # User A admin peut voir les données de Company A
    request_a_admin = factory.get('/')
    request_a_admin.user = user_a_admin
    access_admin_to_a = permission_company.has_object_permission(request_a_admin, None, zone_a)
    print(f'User A admin peut voir Zone A: {access_admin_to_a} (TRUE attendu)')

    # User A admin ne peut pas voir les données de Company B
    access_admin_to_b = permission_company.has_object_permission(request_a_admin, None, zone_b)
    print(f'User A admin peut voir Zone B: {access_admin_to_b} (FALSE attendu)')

    # Superadmin peut tout voir
    request_super = factory.get('/')
    request_super.user = superadmin
    access_super_to_a = permission_company.has_object_permission(request_super, None, zone_a)
    access_super_to_b = permission_company.has_object_permission(request_super, None, zone_b)
    print(f'Superadmin peut voir Zone A: {access_super_to_a} (TRUE attendu)')
    print(f'Superadmin peut voir Zone B: {access_super_to_b} (TRUE attendu)')

    # Test 2: Permissions par rôle
    permission_admin = IsAdminOrSuperAdmin()
    permission_supervisor = IsSupervisorOrAbove()

    # Commercial n'a pas accès admin
    admin_access_commercial = permission_admin.has_permission(request_a, None)
    supervisor_access_commercial = permission_supervisor.has_permission(request_a, None)
    print(f'Commercial a accès admin: {admin_access_commercial} (FALSE attendu)')
    print(f'Commercial a accès supervisor: {supervisor_access_commercial} (FALSE attendu)')

    # Admin a accès admin et supervisor
    admin_access_admin = permission_admin.has_permission(request_a_admin, None)
    supervisor_access_admin = permission_supervisor.has_permission(request_a_admin, None)
    print(f'Admin a accès admin: {admin_access_admin} (TRUE attendu)')
    print(f'Admin a accès supervisor: {supervisor_access_admin} (TRUE attendu)')

    # Superadmin a tout accès
    admin_access_super = permission_admin.has_permission(request_super, None)
    supervisor_access_super = permission_supervisor.has_permission(request_super, None)
    print(f'Superadmin a accès admin: {admin_access_super} (TRUE attendu)')
    print(f'Superadmin a accès supervisor: {supervisor_access_super} (TRUE attendu)')

    print('\n=== RÉSULTATS DES TESTS ===')
    
    # Vérifications finales
    all_tests_passed = True
    
    if access_a_to_b != False:
        print('ERREUR: User A commercial ne devrait pas voir Zone B')
        all_tests_passed = False
    if access_a_to_a != True:
        print('ERREUR: User A commercial devrait voir Zone A')
        all_tests_passed = False
    if access_admin_to_a != True:
        print('ERREUR: User A admin devrait voir Zone A')
        all_tests_passed = False
    if access_admin_to_b != False:
        print('ERREUR: User A admin ne devrait pas voir Zone B')
        all_tests_passed = False
    if access_super_to_a != True or access_super_to_b != True:
        print('ERREUR: Superadmin devrait tout voir')
        all_tests_passed = False
    if admin_access_commercial != False or supervisor_access_commercial != False:
        print('ERREUR: Commercial ne devrait pas avoir accès admin/supervisor')
        all_tests_passed = False
    if admin_access_admin != True or supervisor_access_admin != True:
        print('ERREUR: Admin devrait avoir accès admin/supervisor')
        all_tests_passed = False
    if admin_access_super != True or supervisor_access_super != True:
        print('ERREUR: Superadmin devrait avoir tout accès')
        all_tests_passed = False
    
    if all_tests_passed:
        print('Isolation entre companies: VALIDÉE')
        print('Permissions par rôle: VALIDÉES') 
        print('Superadmin accès complet: VALIDÉ')
        print('\nTous les tests passent avec succès! Le ticket est terminé.')
        return True
    else:
        print('\nCertains tests ont échoué!')
        return False

if __name__ == '__main__':
    success = run_final_tests()
    sys.exit(0 if success else 1)
