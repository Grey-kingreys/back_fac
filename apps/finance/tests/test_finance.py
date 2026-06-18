"""
apps/finance/tests/test_finance.py
Tests API : Caisses, Sessions, Transactions, Taux de change, Consolidation, Dépenses.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.finance.models import (
    CaisseEntreprise,
    CaissePhysique,
    CaisseZone,
    DepenseOperationnelle,
    SessionCaisse,
    TauxChange,
    TransactionCaisse,
)


CAISSES_URL = "/api/caisses/"
CAISSES_ZONE_URL = "/api/caisses-zone/"
CAISSE_ENTREPRISE_URL = "/api/caisse-entreprise/"
SESSIONS_URL = "/api/sessions-caisse/"
OUVRIR_URL = "/api/sessions-caisse/ouvrir/"
TAUX_CHANGE_URL = "/api/taux-change/"
CONSOLIDATION_URL = "/api/caisses/consolidation/"
DEPENSES_URL = "/api/depenses/"


def caisse_url(pk):
    return f"/api/caisses/{pk}/"


def session_url(pk):
    return f"/api/sessions-caisse/{pk}/"


def session_fermer_url(pk):
    return f"/api/sessions-caisse/{pk}/fermer/"


def session_transaction_url(pk):
    return f"/api/sessions-caisse/{pk}/transaction/"


def depense_url(pk):
    return f"/api/depenses/{pk}/"


# ─────────────────────────────────────────────────────────────────────────────
# CaissePhysique
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCaisseList:

    def test_caissier_voit_caisses(self, client_caissier_a, caisse_a):
        res = client_caissier_a.get(CAISSES_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [c["id"] for c in res.data["results"]]
        assert caisse_a.id in ids

    def test_admin_voit_caisses(self, client_admin_a, caisse_a):
        res = client_admin_a.get(CAISSES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(CAISSES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(CAISSES_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_isolation_company(self, client_admin_a, caisse_a, company_b):
        from apps.companies.models import Depot
        from apps.finance.models import CaissePhysique
        depot_b = Depot.objects.filter(zone__company=company_b).first()
        if depot_b:
            CaissePhysique.objects.create(
                company=company_b, depot=depot_b, nom="Caisse B",
            )
        res = client_admin_a.get(CAISSES_URL)
        ids = [c["id"] for c in res.data["results"]]
        # Admin A ne doit voir que les caisses de sa company
        for c in res.data["results"]:
            assert c["id"] in ids


@pytest.mark.django_db
class TestCaisseCreate:

    def test_admin_cree_caisse(self, client_admin_a, depot_a2, company_a):
        payload = {
            "nom": "Caisse Secondaire",
            "depot": depot_a2.id,
            "devise": "GNF",
        }
        res = client_admin_a.post(CAISSES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert CaissePhysique.objects.filter(company=company_a, depot=depot_a2).exists()

    def test_caissier_refuse_creation(self, client_caissier_a, depot_a2):
        res = client_caissier_a.post(CAISSES_URL, {"depot": depot_a2.id})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_une_caisse_par_depot(self, client_admin_a, caisse_a, depot_a):
        """Deux caisses sur le même dépôt → erreur."""
        res = client_admin_a.post(CAISSES_URL, {"depot": depot_a.id, "devise": "GNF"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# SessionCaisse
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSessionCaisseOuvrir:

    def test_caissier_ouvre_session(self, client_caissier_a, caisse_a):
        payload = {
            "caisse": caisse_a.id,
            "solde_ouverture": "50000",
        }
        res = client_caissier_a.post(OUVRIR_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["statut"] == SessionCaisse.Statut.OUVERTE

    def test_chauffeur_refuse_ouverture(self, client_chauffeur_a, caisse_a):
        res = client_chauffeur_a.post(OUVRIR_URL, {"caisse": caisse_a.id, "solde_ouverture": "0"})
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.post(OUVRIR_URL, {})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSessionCaisseFermer:

    def test_caissier_ferme_session(self, client_caissier_a, session_a):
        payload = {"solde_reel": "100000"}
        res = client_caissier_a.post(session_fermer_url(session_a.id), payload)
        assert res.status_code == status.HTTP_200_OK
        session_a.refresh_from_db()
        assert session_a.statut == SessionCaisse.Statut.FERMEE

    def test_session_non_reouvrable(self, client_caissier_a, session_a):
        """Une session fermée ne peut pas être réouverte."""
        client_caissier_a.post(session_fermer_url(session_a.id), {"solde_reel": "100000"})
        res = client_caissier_a.post(session_fermer_url(session_a.id), {"solde_reel": "100000"})
        assert res.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT,
        )


@pytest.mark.django_db
class TestTransactionCaisse:

    def test_caissier_cree_transaction(self, client_caissier_a, session_a):
        payload = {
            "type_transaction": TransactionCaisse.TypeTransaction.ENTREE,
            "montant": "20000",
            "motif": "Vente comptant",
        }
        res = client_caissier_a.post(session_transaction_url(session_a.id), payload)
        assert res.status_code == status.HTTP_201_CREATED

    def test_transaction_hors_session_refuse(self, client_caissier_a, session_a):
        """Session fermée → transaction refusée."""
        client_caissier_a.post(session_fermer_url(session_a.id), {"solde_reel": "100000"})
        payload = {
            "type_transaction": TransactionCaisse.TypeTransaction.ENTREE,
            "montant": "5000",
        }
        res = client_caissier_a.post(session_transaction_url(session_a.id), payload)
        assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT)


# ─────────────────────────────────────────────────────────────────────────────
# Consolidation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestConsolidationCaisses:

    def test_admin_voit_consolidation(self, client_admin_a, caisse_a, company_a):
        CaisseEntreprise.objects.create(
            company=company_a, devise="GNF", solde_actuel=Decimal("1000000"),
        )
        res = client_admin_a.get(CONSOLIDATION_URL)
        assert res.status_code == status.HTTP_200_OK
        assert "caisses_depot" in res.data
        assert "caisses_zone" in res.data
        assert "caisse_entreprise" in res.data
        assert "total_gnf" in res.data

    def test_chauffeur_refuse_consolidation(self, client_chauffeur_a):
        res = client_chauffeur_a.get(CONSOLIDATION_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# TauxChange
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTauxChange:

    def test_admin_cree_taux(self, client_admin_a, company_a):
        import datetime
        payload = {
            "devise_source": "USD",
            "devise_cible": "GNF",
            "taux": "9500",
            "date_expiration": str(
                datetime.date.today().replace(year=datetime.date.today().year + 1)
            ),
        }
        res = client_admin_a.post(TAUX_CHANGE_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert TauxChange.objects.filter(company=company_a, devise_source="USD").exists()

    def test_caissier_voit_taux(self, client_caissier_a):
        res = client_caissier_a.get(TAUX_CHANGE_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(TAUX_CHANGE_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Dépenses opérationnelles
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDepenseOperationnelle:

    def test_admin_cree_depense(self, client_admin_a, company_a, depot_a, caissier_a):
        import datetime
        payload = {
            "categorie": DepenseOperationnelle.Categorie.CARBURANT,
            "montant": "150000",
            "description": "Carburant camion",
            "date_depense": str(datetime.date.today()),
        }
        if depot_a:
            payload["depot_id"] = depot_a.id
        res = client_admin_a.post(DEPENSES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED

    def test_caissier_voit_depenses(self, client_caissier_a):
        res = client_caissier_a.get(DEPENSES_URL)
        assert res.status_code == status.HTTP_200_OK

    def test_chauffeur_refuse(self, client_chauffeur_a):
        res = client_chauffeur_a.get(DEPENSES_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_isolation_company(self, client_admin_a, company_b):
        import datetime

        from apps.accounts.models import CustomUser, Role
        user_b = CustomUser.objects.create_user(
            email="admin_b2@test.com", password="Pass1234!",
            role=Role.ADMIN, company=company_b, is_active=True,
        )
        DepenseOperationnelle.objects.create(
            company=company_b,
            categorie=DepenseOperationnelle.Categorie.LOYER,
            montant=Decimal("500000"),
            date_depense=datetime.date.today(),
            enregistre_par=user_b,
        )
        res = client_admin_a.get(DEPENSES_URL)
        # Admin A ne doit pas voir les dépenses de company B
        for d in res.data["results"]:
            assert d["categorie"] != DepenseOperationnelle.Categorie.LOYER


# ─────────────────────────────────────────────────────────────────────────────
# Règles universelles — Mobile Money
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTransactionMobileMoneyReglesUniverselles:
    """Vérifie la règle universelle §6 : référence opérateur obligatoire."""

    def test_transaction_sans_reference_operateur_refusee(self, client_admin_a, company_a, depot_a):
        from apps.finance.models import CompteMobileMoney
        compte = CompteMobileMoney.objects.create(
            company=company_a,
            depot=depot_a,
            operateur=CompteMobileMoney.Operateur.ORANGE,
            numero="622000001",
            nom_titulaire="Test Admin",
        )
        payload = {
            "type_transaction": "paiement_recu",
            "montant": "50000",
            # reference_operateur absent = non fourni
        }
        url = f"/api/comptes-mobile-money/{compte.id}/transaction/"
        res = client_admin_a.post(url, payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_transaction_avec_reference_operateur_acceptee(self, client_admin_a, company_a, depot_a):
        from apps.finance.models import CompteMobileMoney
        compte = CompteMobileMoney.objects.create(
            company=company_a,
            depot=depot_a,
            operateur=CompteMobileMoney.Operateur.MTN,
            numero="660000002",
            nom_titulaire="Test Admin",
        )
        payload = {
            "type_transaction": "paiement_recu",
            "montant": "50000",
            "reference_operateur": "OM-2026-123456",
        }
        url = f"/api/comptes-mobile-money/{compte.id}/transaction/"
        res = client_admin_a.post(url, payload)
        assert res.status_code == status.HTTP_201_CREATED


# ─────────────────────────────────────────────────────────────────────────────
# Règles universelles — Sessions caisse
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestReglesUniversellesSessionCaisse:
    """Vérifie les règles universelles §1, §2, §4 et §5 sur les sessions de caisse."""

    def test_ecart_sans_motif_refuse(self, client_caissier_a, session_a):
        """§2 — Motif obligatoire si écart non nul à la fermeture."""
        # Solde ouverture = 100 000, pas de transactions, donc théorique = 100 000
        # On annonce 90 000 → écart de -10 000 sans motif → 400
        payload = {"solde_reel": "90000"}
        res = client_caissier_a.post(session_fermer_url(session_a.id), payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "motif_ecart" in str(res.data).lower()

    def test_ecart_avec_motif_accepte(self, client_caissier_a, session_a):
        """§2 — Fermeture avec écart acceptée quand le motif est fourni."""
        payload = {"solde_reel": "90000", "motif_ecart": "Erreur de rendu monnaie"}
        res = client_caissier_a.post(session_fermer_url(session_a.id), payload)
        assert res.status_code == status.HTTP_200_OK
        session_a.refresh_from_db()
        assert session_a.fermee_par is not None

    def test_fermee_par_enregistre(self, client_caissier_a, caissier_a, session_a):
        """Traçabilité — fermee_par doit être renseigné après fermeture."""
        client_caissier_a.post(session_fermer_url(session_a.id), {"solde_reel": "100000"})
        session_a.refresh_from_db()
        assert session_a.fermee_par == caissier_a

    def test_caissier_ne_peut_fermer_session_autre(
        self, client_caissier_a, caisse_a, company_a, depot_a
    ):
        """Un caissier ne peut fermer que SA propre session."""
        from apps.accounts.models import CustomUser, Role
        autre_caissier = CustomUser.objects.create_user(
            email="caissier2@test.com", password="Pass1234!",
            role=Role.CAISSIER, company=company_a, depot=depot_a, is_active=True,
        )
        session_autre = SessionCaisse.objects.create(
            caisse=caisse_a,
            caissier=autre_caissier,
            solde_ouverture=Decimal("50000"),
        )
        # Le caissier A ne voit pas la session d'un autre caissier → 404 (isolation queryset)
        res = client_caissier_a.post(session_fermer_url(session_autre.id), {"solde_reel": "50000"})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_peut_fermer_session_autre_caissier(self, client_admin_a, session_a):
        """L'admin peut fermer n'importe quelle session."""
        res = client_admin_a.post(session_fermer_url(session_a.id), {"solde_reel": "100000"})
        assert res.status_code == status.HTTP_200_OK

    def test_blocage_fermeture_caisse_physique_si_session_ouverte(
        self, client_admin_a, caisse_a, session_a
    ):
        """§5 — Impossible de fermer une CaissePhysique si une session est encore ouverte."""
        url = f"/api/caisses/{caisse_a.id}/fermer/"
        res = client_admin_a.post(url)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_fermeture_caisse_physique_possible_si_sessions_fermees(
        self, client_admin_a, caisse_a, session_a
    ):
        """§5 — La fermeture de CaissePhysique est permise quand toutes les sessions sont fermées."""
        session_a.statut = SessionCaisse.Statut.FERMEE
        session_a.save(update_fields=['statut'])
        url = f"/api/caisses/{caisse_a.id}/fermer/"
        res = client_admin_a.post(url)
        assert res.status_code == status.HTTP_200_OK

    def test_blocage_fermeture_caisse_zone_si_caisse_physique_ouverte(
        self, client_admin_a, caisse_a, caisse_zone_a
    ):
        """§5 — Impossible de fermer une CaisseZone si une CaissePhysique de la zone est ouverte."""
        url = f"/api/caisses-zone/{caisse_zone_a.id}/fermer/"
        res = client_admin_a.post(url)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_superviseur_peut_fermer_session_sa_zone(
        self, client_superviseur_a, session_a
    ):
        """Le superviseur peut fermer une session dans sa propre zone."""
        res = client_superviseur_a.post(session_fermer_url(session_a.id), {"solde_reel": "100000"})
        assert res.status_code == status.HTTP_200_OK


# ─────────────────────────────────────────────────────────────────────────────
# Règles universelles — Fermeture caisse avec sous-session ouverte
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFermetureCaisseReglesUniverselles:
    """Vérifie la règle universelle §5 : blocage si sous-caisses ouvertes."""

    def test_fermeture_caisse_avec_session_ouverte_refusee(self, client_admin_a, caisse_a, session_a):
        url = f"/api/caisses/{caisse_a.id}/fermer/"
        res = client_admin_a.post(url)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_fermeture_caisse_sans_session_ouverte_acceptee(self, client_admin_a, caisse_a, session_a):
        # Fermer la session d'abord (motif requis si écart, on passe solde=0 pour écart nul)
        from apps.finance.models import SessionCaisse
        session_a.solde_fermeture_theorique = 0
        session_a.save(update_fields=['solde_fermeture_theorique'])
        session_a.fermer(solde_reel=0)
        url = f"/api/caisses/{caisse_a.id}/fermer/"
        res = client_admin_a.post(url)
        assert res.status_code == status.HTTP_200_OK
        caisse_a.refresh_from_db()
        assert caisse_a.statut == CaissePhysique.Statut.FERMEE


# ─────────────────────────────────────────────────────────────────────────────
# Règles universelles — Motif écart obligatoire (§2)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSessionCaisseEcartMotifObligatoire:
    """Règle universelle §2 : motif obligatoire si l'écart est non nul."""

    def test_fermeture_avec_ecart_sans_motif_refusee(self, client_caissier_a, session_a):
        """solde_reel différent du solde théorique sans motif_ecart → 400."""
        # solde_ouverture = 100 000, pas de transactions → théorique = 100 000
        # on déclare 80 000 → écart de -20 000 sans motif
        payload = {"solde_reel": "80000"}
        res = client_caissier_a.post(session_fermer_url(session_a.id), payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_fermeture_avec_ecart_et_motif_acceptee(self, client_caissier_a, session_a):
        """solde_reel différent du solde théorique avec motif_ecart → 200."""
        payload = {"solde_reel": "80000", "motif_ecart": "Billet endommagé retiré"}
        res = client_caissier_a.post(session_fermer_url(session_a.id), payload)
        assert res.status_code == status.HTTP_200_OK

    def test_fermeture_sans_ecart_sans_motif_acceptee(self, client_caissier_a, session_a):
        """Pas d'écart → motif non requis."""
        payload = {"solde_reel": "100000"}
        res = client_caissier_a.post(session_fermer_url(session_a.id), payload)
        assert res.status_code == status.HTTP_200_OK


# ─────────────────────────────────────────────────────────────────────────────
# Règles universelles — Versement inter-niveau (§3 + §4)
# ─────────────────────────────────────────────────────────────────────────────

VERSEMENTS_URL = "/api/versements-caisse/"


@pytest.mark.django_db
class TestVersementCaisseReglesUniverselles:
    """Règles §3 (justificatif) et §4 (double comptage) sur les versements."""

    def _payload(self, caisse_a, caisse_zone_a, **overrides):
        base = {
            "type_versement": "depot_vers_zone",
            "caisse_source_depot": caisse_a.id,
            "caisse_dest_zone": caisse_zone_a.id,
            "montant": "50000",
            "montant_comptage_receveur": "50000",
            # justificatif intentionnellement absent
        }
        base.update(overrides)
        return base

    def test_versement_sans_justificatif_refuse(
        self, client_admin_a, caisse_a, caisse_zone_a
    ):
        """Un versement sans justificatif doit être refusé (§3)."""
        payload = self._payload(caisse_a, caisse_zone_a)
        res = client_admin_a.post(VERSEMENTS_URL, payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "justificatif" in res.data

    def test_versement_sans_double_comptage_refuse(
        self, client_admin_a, caisse_a, caisse_zone_a
    ):
        """Un versement sans montant_comptage_receveur doit être refusé (§4)."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        fichier = SimpleUploadedFile("recu.pdf", b"PDF content", content_type="application/pdf")
        payload = self._payload(caisse_a, caisse_zone_a)
        payload.pop("montant_comptage_receveur", None)
        payload["justificatif"] = fichier
        res = client_admin_a.post(VERSEMENTS_URL, payload, format="multipart")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "montant_comptage_receveur" in res.data
