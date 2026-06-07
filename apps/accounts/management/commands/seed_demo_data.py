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
        self._seed_caisses(company, zones, depots)
        self._seed_fidelite(company)
        self._seed_clients(company)
        self._seed_produits(company)

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

    # ── Caisses (hiérarchie finance) ──────────────────────────────────────────

    def _seed_caisses(self, company, zones, depots):
        try:
            from apps.finance.models import CaisseEntreprise, CaissePhysique, CaisseZone

            caisse_ent, created = CaisseEntreprise.objects.get_or_create(
                company=company,
                defaults={"nom": "Caisse Centrale DjoulaGest", "devise": "GNF", "solde_actuel": 0},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ CaisseEntreprise créée  : {caisse_ent.nom}"))
            else:
                self.stdout.write(f"  · CaisseEntreprise existante : {caisse_ent.nom}")

            for zone in zones.values():
                caisse_zone, created = CaisseZone.objects.get_or_create(
                    zone=zone,
                    defaults={
                        "company": company,
                        "nom": f"Caisse Zone {zone.name}",
                        "devise": "GNF",
                        "solde_actuel": 0,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ CaisseZone créée        : {caisse_zone.nom}"))
                else:
                    self.stdout.write(f"  · CaisseZone existante     : {caisse_zone.nom}")

            for depot in depots.values():
                caisse_phys, created = CaissePhysique.objects.get_or_create(
                    depot=depot,
                    defaults={
                        "company": company,
                        "nom": f"Caisse {depot.code}",
                        "devise": "GNF",
                        "solde_actuel": 0,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ CaissePhysique créée    : {caisse_phys.nom}"))
                else:
                    self.stdout.write(f"  · CaissePhysique existante : {caisse_phys.nom}")

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ Caisses ignorées (migration manquante ?) : {e}"))

    # ── Paramètres de fidélité ─────────────────────────────────────────────────

    def _seed_fidelite(self, company):
        try:
            from apps.ventes.models import ParametresFidelite

            params, created = ParametresFidelite.objects.get_or_create(
                company=company,
                defaults={
                    "is_active": True,
                    "tranche_montant": 10000,
                    "points_par_tranche": 1,
                    "valeur_point_gnf": 100,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ ParametresFidelite créés : company={company.name}"))
            else:
                self.stdout.write(f"  · ParametresFidelite existants : company={company.name}")

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ ParametresFidelite ignorés (migration manquante ?) : {e}"))

    # ── Clients démo ──────────────────────────────────────────────────────────

    def _seed_clients(self, company):
        try:
            from apps.ventes.models import Client

            clients_demo = [
                {"code": "CLT-001", "nom": "Mamadou", "prenom": "Diallo", "telephone": "620000001"},
                {"code": "CLT-002", "nom": "Fatoumata", "prenom": "Camara", "telephone": "620000002"},
                {"code": "CLT-003", "nom": "Ibrahim", "prenom": "Bah", "telephone": "620000003"},
            ]
            for c in clients_demo:
                client, created = Client.objects.get_or_create(
                    company=company,
                    code=c["code"],
                    defaults=c,
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Client créé             : {c['prenom']} {c['nom']} ({c['code']})"))
                else:
                    self.stdout.write(f"  · Client existant          : {c['prenom']} {c['nom']} ({c['code']})")

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ Clients ignorés (migration manquante ?) : {e}"))

    # ── Produits et catégories démo ────────────────────────────────────────────

    def _seed_produits(self, company):
        try:
            from apps.produits.models import Categorie, Produit, Unite

            cat, created = Categorie.objects.get_or_create(
                company=company,
                name="Alimentation",
                defaults={"couleur": "#10b981", "tva_taux": 0},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Catégorie créée         : {cat.name}"))
            else:
                self.stdout.write(f"  · Catégorie existante      : {cat.name}")

            unite, created = Unite.objects.get_or_create(
                company=company,
                symbole="kg",
                defaults={"name": "Kilogramme"},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Unité créée             : {unite.name} ({unite.symbole})"))
            else:
                self.stdout.write(f"  · Unité existante          : {unite.name} ({unite.symbole})")

            produits_demo = [
                {
                    "reference": "PROD-001",
                    "nom": "Riz local 25kg",
                    "categorie": cat,
                    "unite": unite,
                    "prix_achat": 150000,
                    "prix_vente": 180000,
                    "seuil_alerte": 10,
                    "tva_taux": 0,
                },
                {
                    "reference": "PROD-002",
                    "nom": "Huile de palme 5L",
                    "categorie": cat,
                    "unite": unite,
                    "prix_achat": 45000,
                    "prix_vente": 55000,
                    "seuil_alerte": 20,
                    "tva_taux": 0,
                },
            ]
            for p in produits_demo:
                produit, created = Produit.objects.get_or_create(
                    company=company,
                    reference=p["reference"],
                    defaults=p,
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Produit créé            : {produit.nom} ({produit.reference})"))
                else:
                    self.stdout.write(f"  · Produit existant         : {produit.nom} ({produit.reference})")

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ Produits ignorés (migration manquante ?) : {e}"))
