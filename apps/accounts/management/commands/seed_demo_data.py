"""
seed_demo_data.py — Données de démo pour DjoulaGest

Crée (si inexistants) :
  - 1 entreprise demo
  - 3 zones géographiques (Conakry, Kindia, Labé)
  - 4 dépôts
  - 7 utilisateurs (un par rôle opérationnel)

Idempotent : vérifie l'existence avant chaque création.
Les produits seront seedés à la Phase 3 (app produits non encore activée).
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import Role
from apps.companies.models import Company, Depot, Zone


User = get_user_model()

# ── Données de référence ──────────────────────────────────────────────────────

COMPANY = {
    "name": "DjoulaGest Guinée SARL",
    "subscription_plan": "PRO",
    "is_active": True,
}

ZONES = [
    {
        "name": "Conakry",
        "code": "CON",
        "description": "Capitale — siège principal",
        "latitude": "9.537000",
        "longitude": "-13.677300",
        "is_active": True,
    },
    {
        "name": "Kindia",
        "code": "KIN",
        "description": "Zone secondaire — Basse Guinée",
        "latitude": "10.058300",
        "longitude": "-12.866700",
        "is_active": True,
    },
    {
        "name": "Labé",
        "code": "LAB",
        "description": "Zone tertiaire — Moyenne Guinée (Fouta Djallon)",
        "latitude": "11.316700",
        "longitude": "-12.283300",
        "is_active": True,
    },
]

# zone_code -> liste de dépôts
DEPOTS = {
    "CON": [
        {
            "name": "Dépôt Central Conakry",
            "code": "DEP-CON-01",
            "address": "Almamya, Commune de Kaloum, Conakry",
            "is_active": True,
        },
        {
            "name": "Dépôt Ratoma",
            "code": "DEP-CON-02",
            "address": "Ratoma, Conakry",
            "is_active": True,
        },
    ],
    "KIN": [
        {
            "name": "Dépôt Kindia Principal",
            "code": "DEP-KIN-01",
            "address": "Centre-ville, Kindia",
            "is_active": True,
        },
    ],
    "LAB": [
        {
            "name": "Dépôt Labé Principal",
            "code": "DEP-LAB-01",
            "address": "Centre-ville, Labé",
            "is_active": True,
        },
    ],
}

DEMO_PASSWORD = "Demo1234!"

# (email, prénom, nom, role, depot_code, phone)
USERS = [
    (
        "admin@djoulagest.com",
        "Ibrahima",
        "Conté",
        Role.ADMIN,
        "DEP-CON-01",
        "+224 620 00 00 01",
    ),
    (
        "superviseur@djoulagest.com",
        "Mariama",
        "Diallo",
        Role.SUPERVISEUR,
        "DEP-CON-01",
        "+224 620 00 00 02",
    ),
    (
        "stock@djoulagest.com",
        "Ousmane",
        "Bah",
        Role.GESTIONNAIRE_STOCK,
        "DEP-CON-01",
        "+224 620 00 00 03",
    ),
    (
        "caissier@djoulagest.com",
        "Fatoumata",
        "Camara",
        Role.CAISSIER,
        "DEP-CON-01",
        "+224 620 00 00 04",
    ),
    (
        "chauffeur@djoulagest.com",
        "Mamadou",
        "Sylla",
        Role.CHAUFFEUR,
        "DEP-CON-02",
        "+224 620 00 00 05",
    ),
    (
        "commercial@djoulagest.com",
        "Aissatou",
        "Barry",
        Role.COMMERCIAL,
        "DEP-KIN-01",
        "+224 620 00 00 06",
    ),
    (
        "maintenancier@djoulagest.com",
        "Thierno",
        "Sow",
        Role.MAINTENANCIER,
        "DEP-LAB-01",
        "+224 620 00 00 07",
    ),
]


# ── Commande ──────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = "Crée les données de démo (entreprise, zones, dépôts, utilisateurs) — idempotent"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n── Seed données de démo ──"))

        company = self._seed_company()
        zones = self._seed_zones(company)
        depots = self._seed_depots(zones)
        self._seed_users(company, depots)

        self.stdout.write(self.style.SUCCESS("✓ Seed terminé.\n"))

    # ── Company ───────────────────────────────────────────────────────────────

    def _seed_company(self):
        company, created = Company.objects.get_or_create(
            name=COMPANY["name"],
            defaults={
                "subscription_plan": COMPANY["subscription_plan"],
                "is_active": COMPANY["is_active"],
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Entreprise créée    : {company.name}"))
        else:
            self.stdout.write(f"  · Entreprise existante : {company.name}")
        return company

    # ── Zones ─────────────────────────────────────────────────────────────────

    def _seed_zones(self, company):
        zones = {}
        for data in ZONES:
            zone, created = Zone.objects.get_or_create(
                code=data["code"],
                defaults={
                    "company": company,
                    "name": data["name"],
                    "description": data["description"],
                    "latitude": data["latitude"],
                    "longitude": data["longitude"],
                    "is_active": data["is_active"],
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Zone créée          : {zone.name} ({zone.code})"))
            else:
                self.stdout.write(f"  · Zone existante      : {zone.name} ({zone.code})")
            zones[zone.code] = zone
        return zones

    # ── Dépôts ────────────────────────────────────────────────────────────────

    def _seed_depots(self, zones):
        depots = {}
        for zone_code, depot_list in DEPOTS.items():
            zone = zones.get(zone_code)
            if not zone:
                self.stdout.write(self.style.WARNING(f"  ⚠ Zone {zone_code} introuvable — dépôts ignorés"))
                continue
            for data in depot_list:
                depot, created = Depot.objects.get_or_create(
                    code=data["code"],
                    defaults={
                        "zone": zone,
                        "name": data["name"],
                        "address": data["address"],
                        "is_active": data["is_active"],
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Dépôt créé         : {depot.name} ({depot.code})"))
                else:
                    self.stdout.write(f"  · Dépôt existant     : {depot.name} ({depot.code})")
                depots[depot.code] = depot
        return depots

    # ── Utilisateurs ──────────────────────────────────────────────────────────

    def _seed_users(self, company, depots):
        for email, first_name, last_name, role, depot_code, phone in USERS:
            if User.objects.filter(email=email).exists():
                self.stdout.write(f"  · Utilisateur existant: {email}")
                continue

            depot = depots.get(depot_code)
            if not depot:
                self.stdout.write(self.style.WARNING(f"  ⚠ Dépôt {depot_code} introuvable — {email} ignoré"))
                continue

            try:
                User.objects.create_user(
                    email=email,
                    password=DEMO_PASSWORD,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    company=company,
                    depot=depot,
                    phone=phone,
                    is_active=True,
                    first_login_done=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Utilisateur créé    : {email} [{role}]")
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Erreur {email} : {e}"))
