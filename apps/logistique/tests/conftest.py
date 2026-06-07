"""
apps/logistique/tests/conftest.py
Fixtures spécifiques à la logistique (véhicules, missions).
"""

from decimal import Decimal

import pytest

from apps.logistique.models import Mission, Vehicule


@pytest.fixture
def vehicule_a(db, company_a):
    return Vehicule.objects.create(
        company=company_a,
        immatriculation="AB-1234-C",
        type_vehicule=Vehicule.TypeVehicule.CAMION,
        marque="Toyota",
        modele="Hilux",
        annee=2020,
        capacite_kg=Decimal("1000"),
        statut=Vehicule.Statut.DISPONIBLE,
    )


@pytest.fixture
def vehicule_b(db, company_b):
    return Vehicule.objects.create(
        company=company_b,
        immatriculation="ZZ-9999-Z",
        type_vehicule=Vehicule.TypeVehicule.CAMION,
        marque="Renault",
        modele="Master",
        annee=2019,
        capacite_kg=Decimal("2000"),
        statut=Vehicule.Statut.DISPONIBLE,
    )


@pytest.fixture
def mission_a(db, company_a, vehicule_a, depot_a, depot_a2, admin_a, chauffeur_a):
    return Mission.objects.create(
        company=company_a,
        vehicule=vehicule_a,
        chauffeur=chauffeur_a,
        depot_depart=depot_a,
        depot_arrivee=depot_a2,
        created_by=admin_a,
        statut=Mission.Statut.PLANIFIEE,
    )
