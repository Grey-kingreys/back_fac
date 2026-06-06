# DjoulaGest — Mémoire Backend

**Dernière mise à jour :** 06/06/2026  
**État CI :** flake8 0 erreur · isort 0 erreur · 142 tests passés · Django system check OK  
**Deadline projet :** 20/06/2026 — **14 jours restants**

---

## Démarrage rapide

```bash
cd backend
docker compose up --build
# API dispo sur http://localhost:8001
# Swagger : http://localhost:8001/api/schema/swagger-ui/
# ReDoc   : http://localhost:8001/api/schema/redoc/
```

L'`entrypoint.sh` exécute automatiquement : wait postgres → migrate → collectstatic → createsuperuser → seed_demo_data → gunicorn.

---

## Apps enregistrées dans INSTALLED_APPS

```python
LOCAL_APPS = [
    'apps.companies',   # ✅ complet
    'apps.accounts',    # ✅ complet
    'apps.produits',    # ⚠️ modèles de base — variantes/import/export/prix zones manquants
    'apps.stocks',      # ⚠️ transferts OK — inventaires et ajustements manquants
    'apps.ventes',      # ⚠️ commandes OK — retours/devis/PDF manquants
    'apps.finance',     # ❌ hiérarchie 4 niveaux non implémentée — critique
    'apps.logistique',  # ⚠️ GPS/signature OK — QR code/maintenance/pannes manquants
    'apps.rh',          # ⚠️ présences/congés OK — historique affectations manquant
]
```

---

## Migrations (toutes appliquées)

| App | Migrations |
|-----|-----------|
| accounts | 0001 → 0005 |
| companies | 0001 → 0003 |
| produits | 0001 |
| stocks | 0001 |
| ventes | 0001 |
| finance | 0001 |
| logistique | 0001 → 0003 |
| rh | 0001 |

---

## Endpoints API existants

Préfixe commun : `/api/`

### Auth (`apps/accounts/urls_auth.py`)
| Méthode | URL | Rôle |
|---------|-----|------|
| POST | `/auth/login/` | JWT access + refresh |
| POST | `/auth/refresh/` | Rafraîchir access token |
| POST | `/auth/logout/` | Blacklist refresh (Redis) |
| GET/PATCH | `/auth/me/` | Profil connecté |
| POST | `/auth/me/change-password/` | Changer mot de passe |
| POST | `/auth/password-reset/` | Envoi email reset (Resend) |
| POST | `/auth/password-reset/confirm/` | Confirme reset (token Redis 1h) |
| GET/POST | `/auth/first-login/` | Flow premier login admin |

### Users & Audit (`apps/accounts/urls.py`)
| Méthode | URL |
|---------|-----|
| GET/POST | `/users/` |
| GET/PATCH/DELETE | `/users/{id}/` |
| POST | `/users/{id}/reset-password/` |
| GET | `/audit-logs/` |
| GET | `/login-logs/` |

### Companies, Zones, Dépôts (`apps/companies/urls.py`)
| Méthode | URL | Note |
|---------|-----|------|
| GET/POST | `/companies/` | SuperAdmin only |
| GET/PATCH | `/companies/{id}/` | |
| POST | `/companies/{id}/toggle/` | |
| GET/POST/PATCH/DELETE | `/zones/` | |
| GET/POST/PATCH/DELETE | `/depots/` | |
| GET | `/depots/{id}/dashboard/` | **⚠️ PLACEHOLDER VIDE** |

### Produits (`/api/`)
| Méthode | URL |
|---------|-----|
| CRUD | `/categories/` |
| CRUD | `/unites/` |
| CRUD | `/fournisseurs/` |
| CRUD | `/produits/` |
| GET | `/produits/{id}/stock/` |

### Stocks (`/api/`)
| Méthode | URL |
|---------|-----|
| GET | `/stocks/` |
| POST | `/stocks/entree/` |
| POST | `/stocks/sortie/` |
| GET | `/mouvements-stock/` |
| CRUD | `/transferts/` |
| POST | `/transferts/{id}/expedier/` |
| POST | `/transferts/{id}/receptionner/` |
| POST | `/transferts/{id}/annuler/` |

### Ventes (`/api/`)
| Méthode | URL |
|---------|-----|
| CRUD | `/clients/` |
| GET/POST | `/commandes/` |
| GET | `/commandes/{id}/` |
| POST | `/commandes/{id}/paiement/` |
| POST | `/commandes/{id}/annuler/` |
| GET/PATCH | `/fidelite/parametres/` |

### Finance (`/api/`)
| Méthode | URL |
|---------|-----|
| CRUD | `/taux-change/` |
| CRUD | `/caisses/` |
| GET | `/sessions-caisse/` |
| POST | `/sessions-caisse/ouvrir/` |
| POST | `/sessions-caisse/{id}/fermer/` |
| POST | `/sessions-caisse/{id}/transaction/` |
| CRUD | `/comptes-mobile-money/` |
| POST | `/comptes-mobile-money/{id}/transaction/` |
| GET | `/comptes-mobile-money/{id}/transactions/` |

### Logistique (`/api/`)
| Méthode | URL |
|---------|-----|
| CRUD | `/vehicules/` |
| CRUD | `/missions/` |
| POST | `/missions/{id}/chargement/` |
| POST | `/missions/{id}/transit/` |
| POST | `/missions/{id}/arrivee/` |
| POST | `/missions/{id}/terminer/` |
| POST | `/missions/{id}/annuler/` |
| POST | `/missions/{id}/position/` |
| GET | `/missions/{id}/positions/` |

### RH (`/api/`)
| Méthode | URL |
|---------|-----|
| CRUD | `/employes/` |
| GET | `/employes/{id}/presences/` |
| GET | `/employes/{id}/conges/` |
| GET | `/employes/{id}/documents/` |
| CRUD | `/presences/` |
| CRUD | `/conges/` |
| POST | `/conges/{id}/approuver/` |
| POST | `/conges/{id}/refuser/` |
| CRUD | `/documents/` |
| CRUD | `/objectifs-vente/` |

---

## Modèles existants

### apps.produits
- `Categorie` : company, name, couleur, is_active
- `Unite` : company, name, symbole
- `Fournisseur` : company, code, nom, solde_dette
- `Produit` : company, reference, categorie, unite, fournisseur_principal, prix_achat/vente, tva_taux, seuil_alerte/max, est_perimable

### apps.stocks
- `StockDepot` : depot + produit (unique_together), quantite, `en_alerte` property
- `LotStock` : stock_depot, numero_lot, quantite, date_expiration → FEFO
- `MouvementStock` : TypeMouvement (entree/sortie/transfert_entrant/sortie_transfert/inventaire), quantite_avant/apres
- `TransfertStock` : auto-numéro `TRF-YYYYMM-NNNN`, Statut (brouillon/en_transit/receptionne/annule)

### apps.ventes
- `ParametresFidelite` : company (OneToOne), tranche_montant, points_par_tranche, valeur_point_gnf
- `Client` : company, code, points_fidelite, solde_credit
- `Commande` : auto-numéro `CMD-YYYYMM-NNNNN`, Statut, ModePaiement, montant_ht/tva/ttc/paye, `reste_a_payer`, `est_solde`
- `LigneCommande` : produit, quantite, prix_unitaire_ht, tva_taux, montant_ht/tva/ttc
- `Paiement` : Mode (especes/mobile_money/virement/cheque/credit)

### apps.finance
- `TauxChange` : company, devise_source, devise_cible, taux, date_expiration, `est_expire` property
- `CaissePhysique` : company, depot (OneToOne), solde_actuel — **niveau dépôt uniquement, manque Zone et Entreprise**
- `SessionCaisse` : caisse, caissier, Statut OUVERTE/FERMEE, motif_ecart — jamais supprimée, jamais réouverte
- `TransactionCaisse` : TypeTransaction (entree/sortie/vente/remboursement/approvisionnement/retrait)
- `CompteMobileMoney` : Operateur (orange_money/mtn_money), company, depot
- `TransactionMobileMoney` : TypeTransaction (depot/retrait/paiement_recu/paiement_envoye)

### apps.logistique
- `Vehicule` : company, immatriculation, type, Statut, has_nfc, nfc_tag — **manque marque/modèle/année/km**
- `Mission` : auto-numéro `MSN-YYYYMM-NNNN`, 7 statuts, signature_arrivee (base64), transfert_stock OneToOne — **manque qr_code**
- `LigneMission` : produit, quantite, quantite_recue
- `PositionGPS` : mission, latitude, longitude, vitesse_kmh

### apps.rh
- `Employe` : company, matricule, user (OneToOne optionnel), depot, salaire_base
- `Presence` : employe + date (unique_together), TypePresence
- `Conge` : TypeConge, Statut, `nb_jours` property
- `Document` : type, fichier — **attaché uniquement à Employe, pas à Commande/Mission/Transfert**
- `ObjectifVente` : depot + annee + mois (unique_together), `taux_realisation` property

---

## Architecture de sécurité multi-tenant

### Règles d'isolation
- **Pattern 1 — FK directe** (`company = FK(Company)`) → `CompanyFilterMixin`
- **Pattern 2 — FK indirecte** → override manuel `get_queryset()` avec `filter(relation__company=...)`

Modèles par pattern :
- **Pattern 1** : Categorie, Unite, Fournisseur, Produit, TransfertStock, Client, TauxChange, CaissePhysique, CompteMobileMoney, Vehicule, Employe, Document, ObjectifVente
- **Pattern 2** : StockDepot, MouvementStock, Commande, SessionCaisse, TransactionCaisse, TransactionMobileMoney, Mission, PositionGPS, Presence, Conge

### Audit automatique
`accounts/apps.py` → `connect_audit_signals()` sur 23 modèles via `pre_save/post_save/post_delete`. Nouveaux modèles à ajouter au fur et à mesure.

---

## Services métier

### `apps/stocks/services.py`
- `entree_stock()` — crée LotStock si périmable, met à jour StockDepot, écrit MouvementStock
- `sortie_stock()` — FEFO sur LotStock, ValidationError si stock insuffisant
- `creer_transfert()` — TransfertStock en brouillon
- `expedier_transfert()` — sortie_stock par ligne, passe en EN_TRANSIT
- `receptionner_transfert()` — entree_stock quantités reçues, passe en RECEPTIONNE

### `apps/ventes/services.py`
- `creer_commande()` — transaction atomique : valide stock, crée Commande + lignes, sortie_stock, points fidélité, paiement initial

---

## Conventions de code

### Isort — sections personnalisées (setup.cfg)
Ordre obligatoire avec une **ligne vide entre chaque section** :
`FUTURE → STDLIB → DJANGO → THIRDPARTY → FIRSTPARTY → LOCALFOLDER`

### flake8 — ignorés globalement
`E501` (longueur), `F401` (imports), `W503/W504` (opérateur binaire)

### Commentaires de section `# ──`
**0 ligne vide** entre le commentaire et la classe — 2 lignes vides avant le commentaire.
```python
# ✅
class Foo: pass


# ── Section ──
class Bar: pass   # ← pas de ligne vide entre comment et class

# ❌ génère E302
# ── Section ──

class Bar: pass
```

### Format de réponse API
- `companies` : enveloppe `{success, data, message}`
- Toutes les autres apps : format DRF standard

---

## Observabilité (LGTM stack)

Entièrement **commenté** dans `docker-compose.yml`. OTel installé — l'app ne crashe pas si Tempo est absent.  
Pour activer : créer `./docker/loki/`, `./docker/mimir/`, `./docker/prometheus/`, `./docker/tempo/`, `./docker/grafana/provisioning/datasources/` puis décommenter les services.

---

## CI (`backend/.github/workflows/backend-ci.yml`)

1. `pip install -r requirements.txt`
2. `flake8 .`
3. `isort --check-only .`
4. `python manage.py migrate`
5. `pytest || [ $? -eq 5 ]`

**État actuel** : 142 tests passent (uniquement `apps/accounts/`). Les autres apps ont des `tests.py` vides.

---

## Données de démo

| Compte | Email | Mdp |
|--------|-------|-----|
| superadmin | superadmin@djoulagest.com | Demo1234! |
| admin | admin@djoulagest.com | Demo1234! |
| superviseur | superviseur@djoulagest.com | Demo1234! |
| gestionnaire_stock | stock@djoulagest.com | Demo1234! |
| caissier | caissier@djoulagest.com | Demo1234! |
| chauffeur | chauffeur@djoulagest.com | Demo1234! |
| commercial | commercial@djoulagest.com | Demo1234! |
| maintenancier | maintenancier@djoulagest.com | Demo1234! |

---

## Fichiers de configuration clés

| Fichier | Rôle |
|---------|------|
| `config/settings.py` | Django, JWT, Redis, CORS, INSTALLED_APPS |
| `config/urls.py` | Routes racine `/api/` |
| `docker-compose.yml` | web, postgres, redis + LGTM commenté |
| `entrypoint.sh` | migrate → seed → gunicorn |
| `setup.cfg` | flake8 + isort (profile black, lines_after_imports=2) |
| `requirements.txt` | Django 5.x, DRF 3.15, SimpleJWT, drf-spectacular, OTel, Resend |

---

---

# ANALYSE DES ÉCARTS CDC — Audit du 06/06/2026

> Résultat d'une lecture exhaustive du `CDC_Final_Groupe1.pdf` comparée au code actuel.
> Légende : ✅ Implémenté · ⚠️ Partiel · ❌ Absent

---

## §3.1 Zones et Dépôts

| Exigence | État | Notes |
|----------|------|-------|
| CRUD zones + GPS latitude/longitude | ✅ | |
| Dépôt → caisse physique | ✅ | CaissePhysique OneToOne |
| Dépôt → comptes Mobile Money | ✅ | CompteMobileMoney FK |
| **Gestionnaire assigné au dépôt** | ❌ | Pas de champ `gestionnaire` sur Depot |
| **Dashboard par dépôt** (stock, solde, historique) | ❌ | `/depots/{id}/dashboard/` = placeholder vide |
| **Transfert de responsabilité entre gestionnaires** | ❌ | Aucun modèle ni endpoint |

## §3.2 Produits

| Exigence | État | Notes |
|----------|------|-------|
| Fiche produit complète | ✅ | |
| **Prix différenciés par zone** | ❌ | Un seul prix — pas de `PrixZone` |
| Seuil stock (champ) | ✅ | `seuil_alerte` |
| **Alerte automatique seuil atteint** | ❌ | Champ présent mais aucun déclencheur |
| Historique mouvements | ✅ | MouvementStock filtrable |
| **Variantes produits** (taille, couleur) | ❌ | Pas de `VarianteProduit` |
| **Import/export catalogue CSV/Excel** | ❌ | Aucun endpoint |
| FEFO périmables | ✅ | LotStock.date_expiration |

## §3.3 Stocks et Mouvements

| Exigence | État | Notes |
|----------|------|-------|
| Approvisionnement / entrée stock | ✅ | |
| Transferts inter-dépôts complets | ✅ | |
| **Inventaires physiques** (comptage + détection écarts) | ❌ | Pas de modèle `Inventaire` |
| **Ajustements de stock** (motif + validation superviseur) | ❌ | Pas de workflow de validation |
| Historique mouvements | ✅ | |
| FIFO/FEFO | ✅ | |

## §3.4 Fournisseurs

| Exigence | État | Notes |
|----------|------|-------|
| Fiche fournisseur | ✅ | |
| **Commandes fournisseurs / livraisons attendues** | ❌ | Pas de `CommandeFournisseur` |
| **Historique achats par fournisseur** | ❌ | MouvementStock ne référence pas le fournisseur |
| **Gestion avances et dettes** | ⚠️ | `solde_dette` existe mais aucun endpoint pour le mouvementer |
| **Évaluation fournisseurs** | ❌ | Pas d'`EvaluationFournisseur` |

## §3.5 Ventes et Clients

| Exigence | État | Notes |
|----------|------|-------|
| Fiches clients | ✅ | |
| Commandes + paiements | ✅ | |
| **Génération factures et bons de livraison PDF** | ❌ | Pas de génération PDF |
| **Suivi créances + relances automatiques** | ❌ | `reste_a_payer` existe mais pas de liste créances ni relance |
| **Retours clients et remboursements** | ❌ | Pas de `RetourCommande` |
| **Remises et promotions** (par produit/client/période) | ⚠️ | Remise globale sur Commande uniquement — pas de `Promotion` |
| **Système de devis → commande** | ❌ | Pas de `Devis` |
| TVA sur factures | ✅ | |

## §3.6 Finance — ZONE CRITIQUE

### Hiérarchie des caisses

| Exigence | État | Notes |
|----------|------|-------|
| **4 niveaux : Entreprise → Zone → Dépôt → Session** | ❌ **CRITIQUE** | Seul niveau Dépôt + Session existent. `CaisseZone` et `CaisseEntreprise` absents |
| Jamais supprimée | ✅ | |
| Jamais réouverte | ✅ | |
| Motif obligatoire pour écarts | ✅ | |
| **Double comptage** (receveur saisit son propre montant) | ❌ | Non modélisé |
| **Justificatif obligatoire versements inter-niveaux** | ❌ | Pas de workflow inter-niveaux |
| **Blocage fermeture si sous-caisses ouvertes** | ❌ | Pas de vérification en cascade |
| **Consolidation automatique à la fermeture** | ❌ | Pas de remontée vers Zone puis Entreprise |

### Comptes Mobile Money

| Exigence | État | Notes |
|----------|------|-------|
| **Même hiérarchie que caisses physiques** | ❌ | Pas de `CompteMobileMoneyZone` ni Entreprise |
| **ID transaction opérateur obligatoire** | ⚠️ | `reference_operateur` optionnel — doit être requis pour paiements reçus |
| **Relevé opérateur comme justificatif à la fermeture** | ❌ | Pas de `SessionCompteMobileMoney` |
| **Comparaison solde virtuel vs relevé réel** | ❌ | |

### Autres fonctionnalités financières

| Exigence | État | Notes |
|----------|------|-------|
| **Dépenses opérationnelles par catégorie** (carburant, maintenance, salaires) | ❌ | Pas de `DepenseOperationnelle` |
| **Rapports financiers** (journal, bilan, état créances) | ❌ | Pas d'endpoints de rapport |
| **Alertes anomalies financières** | ❌ | |
| Taux de change avec expiration | ✅ | `TauxChange.est_expire` |
| **Alerte à l'expiration d'un taux** | ❌ | Propriété calcule mais pas d'alerte |
| **Devise assignée à chaque caisse** | ❌ | `CaissePhysique` sans champ `devise` |
| **Vue consolidée soldes + conversion devise principale** | ❌ | Pas d'endpoint de consolidation |

## §3.7 Logistique

| Exigence | État | Notes |
|----------|------|-------|
| Fiche véhicule (immatriculation, statut, NFC) | ✅ | |
| **Marque, modèle, année, capacité de charge** | ❌ | Champs absents sur `Vehicule` |
| **Kilométrage et consommation carburant** | ❌ | Aucun champ sur `Vehicule` ni `Mission` |
| **Maintenance préventive et corrective** | ❌ | Pas de modèle `Maintenance` |
| **Maintenance prédictive** (alertes km/calendaire) | ❌ | |
| **Gestion des pannes** (déclaration, suivi, coût) | ❌ | Pas de modèle `Panne` |
| **Documents véhicule** (assurance, visite technique + rappels expiration) | ❌ | Pas de `DocumentVehicule` |
| **QR code généré à la création de mission** | ❌ | Champ `qr_code` absent sur `Mission` |
| GPS tracking (PositionGPS) | ✅ | |
| Signature Canvas HTML5 | ✅ | `signature_arrivee` base64 |
| **Bon de livraison PDF signé auto** | ❌ | Pas de génération PDF |
| Statut Litige | ✅ | |

## §3.8 Tableau de Bord Logistique

| Exigence | État | Notes |
|----------|------|-------|
| Liste missions actives filtrables | ✅ | |
| Historique trajets / positions | ✅ | `/missions/{id}/positions/` |
| **Alertes automatiques** (arrêt prolongé, retard, perte signal, litige) | ❌ | Pas de système d'alerte |

## §3.9 Planification Transferts de Stock

| Exigence | État | Notes |
|----------|------|-------|
| Mode manuel | ✅ | |
| **Mode automatique** (analyse périodique + recommandations) | ❌ | Pas de tâche périodique (Celery) |
| **Notifications** in-app + email à la validation | ❌ | |
| Transfert validé → mission créée automatiquement | ⚠️ | OneToOne existe mais déclenchement non automatique |

## §3.10 RH

| Exigence | État | Notes |
|----------|------|-------|
| Fiche employé, présences, congés | ✅ | |
| **Historique affectations / mutations entre dépôts** | ❌ | Pas de `HistoriqueAffectation` |

## §3.11 Utilisateurs et Rôles

| Exigence | État | Notes |
|----------|------|-------|
| Rôles + audit + lockout + journal connexion | ✅ | |
| **Permissions granulaires par utilisateur** (lecture/écriture/validation affinables) | ❌ | Uniquement role-based global |

## §3.12 Fidélité Client

| Exigence | État | Notes |
|----------|------|-------|
| Attribution + conversion points | ✅ | |
| Configuration par admin | ✅ | ParametresFidelite |
| **Historique des points par client** | ❌ | Seulement le solde — pas de `HistoriquePoints` |
| **Notifications à l'atteinte d'un seuil** | ❌ | |

## §3.13 Gestion Documentaire

| Exigence | État | Notes |
|----------|------|-------|
| Upload et stockage documents | ✅ | |
| **Rattachement à une opération** (Commande, Mission, Transfert) | ❌ | Document attaché à Employe uniquement |
| **Recherche par catégorie, date, opération** | ❌ | Pas de filtres avancés |

## §3.14 TVA

| Exigence | État | Notes |
|----------|------|-------|
| Taux TVA par produit + calcul HT/TTC | ✅ | |
| **Taux TVA par catégorie de produit** | ❌ | `Categorie` sans champ `tva_taux` |
| **Rapport TVA collectée par période** | ❌ | |

## §3.15 SaaS Multi-Entreprise

| Exigence | État | Notes |
|----------|------|-------|
| CRUD companies + isolation + toggle | ✅ | |
| **Tableau de bord superadmin agrégé** | ❌ | Pas d'endpoint statistiques globales |
| **Système de facturation/abonnement** | ❌ | `subscription_plan` existe mais pas de billing |

## §4 Fonctionnalités Transversales

| Exigence | État | Notes |
|----------|------|-------|
| **Dashboard analytique** (KPIs, CA, graphiques, top produits) | ❌ | Entièrement absent |
| **Export rapports PDF / Excel** | ❌ | |
| **Système de notifications in-app** | ❌ | Pas de modèle `Notification` |
| **Alertes automatiques** (rupture stock, échéances, caisses) | ❌ | |
| **Messagerie interne** | ❌ | Pas de modèle `Message`/`Conversation` |
| Objectifs commerciaux (modèle) | ✅ | ObjectifVente |
| **Rapport de performance commerciale** | ❌ | |
| API Swagger | ✅ | drf-spectacular |

---

---

# PLAN DE PROGRESSION — Résolution des écarts

> Organisé par priorité CDC, regroupé pour minimiser les migrations.  
> Chaque sprint correspond à 1–2 jours de travail.  
> **Deadline : 20/06/2026**

---

## Sprint 1 — Corrections modèles existants *(Jour 1)*
> Modifications de modèles existants → nouvelles migrations. À faire en premier pour éviter les migrations en cascade plus tard.

**`apps/logistique/models.py` — Vehicule + Mission**
- Ajouter sur `Vehicule` : `marque`, `modele`, `annee`, `capacite_charge_kg`, `kilometrage_actuel`
- Ajouter sur `Mission` : `qr_code` (UUIDField unique, auto-généré à la création)
- `makemigrations logistique`

**`apps/finance/models.py` — CaissePhysique**
- Ajouter `devise` (CharField, default `'GNF'`) sur `CaissePhysique`
- `makemigrations finance`

**`apps/produits/models.py` — Categorie**
- Ajouter `tva_taux` (DecimalField, default 0) sur `Categorie`
- `makemigrations produits`

**`apps/rh/models.py` — Document**
- Ajouter FK optionnelles : `commande` (FK Commande null=True), `mission` (FK Mission null=True), `transfert` (FK TransfertStock null=True)
- `makemigrations rh`

**`apps/produits/models.py` — Fournisseur**
- Ajouter `fournisseur` (FK Fournisseur null=True) sur `MouvementStock` dans `apps/stocks/models.py` pour tracer l'achat fournisseur
- `makemigrations stocks`

---

## Sprint 2 — Hiérarchie des caisses *(Jour 2–3)*
> La lacune la plus critique du CDC §3.6.1. Nécessite de nouveaux modèles dans `apps/finance/`.

**Nouveaux modèles à ajouter dans `apps/finance/models.py`** :

```python
# Caisse de niveau Zone
class CaisseZone(models.Model):
    company = FK(Company)
    zone = OneToOne(Zone)
    nom = CharField
    devise = CharField(default='GNF')
    solde_actuel = DecimalField
    is_active = BooleanField
    # jamais supprimée, jamais réouverte

# Caisse de niveau Entreprise
class CaisseEntreprise(models.Model):
    company = OneToOne(Company)
    nom = CharField
    devise = CharField(default='GNF')
    solde_actuel = DecimalField
    is_active = BooleanField

# Versement inter-niveaux (Dépôt→Zone ou Zone→Entreprise)
class VersementCaisse(models.Model):
    TypeVersement = (depot_vers_zone / zone_vers_entreprise)
    caisse_source_depot = FK(CaissePhysique, null=True)
    caisse_source_zone = FK(CaisseZone, null=True)
    caisse_dest_zone = FK(CaisseZone, null=True)
    caisse_dest_entreprise = FK(CaisseEntreprise, null=True)
    montant = DecimalField
    justificatif = FileField  # obligatoire
    montant_comptage_receveur = DecimalField  # double comptage
    ecart = DecimalField (property calculée)
    motif_ecart = TextField
    effectue_par = FK(User)
    recu_par = FK(User)
    created_at = DateTimeField
```

**Règles à implémenter** :
- Blocage fermeture `CaissePhysique` si session ouverte → vérifier dans `fermer()`
- Blocage fermeture `CaisseZone` si une `CaissePhysique` enfant a une session ouverte
- Endpoint `GET /api/caisses/consolidation/` → soldes de tous niveaux avec conversion devise principale

**`makemigrations finance` · nouveaux endpoints** :
- CRUD `/caisses-zone/`
- GET/PATCH `/caisse-entreprise/` (OneToOne par company)
- POST `/versements-caisse/`
- GET `/caisses/consolidation/`

---

## Sprint 3 — QR Code missions + PDF *(Jour 3–4)*
> §3.7 — le mode Standard QR+GPS est **obligatoire** selon le CDC.

**QR Code** (`apps/logistique/`) :
- Ajouter `qrcode` dans `requirements.txt`
- À la création d'une `Mission` (signal `post_save`), générer un QR code UUID et le stocker en base64 ou fichier
- Endpoint `GET /missions/{id}/qr/` → retourne l'image QR (base64 PNG)
- Endpoint `POST /missions/scanner-qr/` → le chauffeur soumet son UUID, valide et passe au statut CHARGEMENT

**Génération PDF** (bibliothèque `weasyprint` ou `reportlab`) :
- `requirements.txt` : ajouter `weasyprint` ou `reportlab`
- Endpoint `GET /commandes/{id}/facture/` → PDF facture avec HT/TTC/TVA/paiements
- Endpoint `GET /commandes/{id}/bon-livraison/` → PDF bon de livraison
- Endpoint `GET /missions/{id}/bon-livraison/` → PDF bon de livraison signé (inclut la signature base64)

---

## Sprint 4 — Dashboard dépôt + Analytics *(Jour 4–5)*
> §3.1 (dashboard dépôt) + §4.1 (KPIs analytiques). Ce sont des endpoints de lecture pure, pas de nouveaux modèles.

**`GET /depots/{id}/dashboard/`** — remplacer le placeholder par des données réelles :
```json
{
  "depot": {...},
  "stock_critique": [...],   // StockDepot où quantite <= seuil_alerte
  "solde_caisse": 0,          // CaissePhysique.solde_actuel
  "sessions_ouvertes": 1,
  "ventes_du_jour": {"count": 0, "montant_ttc": 0},
  "transferts_en_cours": 0,
  "missions_actives": 0
}
```

**Nouveaux endpoints analytics** (dans `apps/companies/views.py` ou app dédiée `apps/analytics/`) :
- `GET /api/analytics/ventes/` — CA par période (params: `debut`, `fin`, `depot`, `zone`)
- `GET /api/analytics/stock/` — rotation stocks, produits en alerte, top produits
- `GET /api/analytics/finance/` — bilan recettes/dépenses, état créances
- `GET /api/analytics/tva/` — TVA collectée par période
- `GET /api/analytics/performance/` — objectifs vs réalisé par dépôt

---

## Sprint 5 — Notifications et Alertes *(Jour 5–6)*
> §4.2 — mentionné dans 6 sections différentes du CDC. Modèle simple, endpoints simples.

**Nouveau modèle** dans `apps/accounts/models.py` ou `apps/notifications/` (app dédiée recommandée) :
```python
class Notification(models.Model):
    TypeNotification = (
        rupture_stock / seuil_stock / ecart_caisse / mission_litige /
        taux_change_expire / echeance_client / transfert_valide /
        conge_approuve / maintenance_vehicule
    )
    destinataire = FK(User)
    company = FK(Company)
    type_notification = CharField
    titre = CharField
    message = TextField
    lien = CharField(blank=True)  # ex: "/commandes/42/"
    est_lue = BooleanField(default=False)
    created_at = DateTimeField
```

**Endpoints** :
- `GET /api/notifications/` — liste non lues + historique
- `POST /api/notifications/{id}/lire/` — marquer comme lue
- `POST /api/notifications/tout-lire/` — tout marquer comme lu

**Déclencheurs** (Django signals dans chaque app) :
- `StockDepot` post_save → si `quantite <= seuil_alerte` → notification gestionnaire_stock + admin
- `SessionCaisse` post_save statut=FERMEE avec ecart → notification admin + superviseur
- `Mission` post_save statut=LITIGE → notification admin + superviseur
- `TauxChange` post_save → si `est_expire` → notification admin
- `TransfertStock` post_save statut=RECEPTIONNE → notification gestionnaire source

---

## Sprint 6 — Stocks : Inventaires + Ajustements *(Jour 6–7)*
> §3.3 — fonctionnalité critique pour la traçabilité.

**Nouveaux modèles dans `apps/stocks/models.py`** :
```python
class Inventaire(models.Model):
    company = FK(Company)
    depot = FK(Depot)
    Statut = (en_cours / valide / annule)
    numero = CharField  # INV-YYYYMM-NNNN
    cree_par = FK(User)
    valide_par = FK(User, null=True)
    created_at, valide_le = DateTimeField

class LigneInventaire(models.Model):
    inventaire = FK(Inventaire)
    produit = FK(Produit)
    quantite_theorique = DecimalField  # lu depuis StockDepot
    quantite_comptee = DecimalField
    ecart = property  # comptée - theorique
    # À la validation : MouvementStock de type "inventaire" pour corriger l'écart

class AjustementStock(models.Model):
    company = FK(Company)
    depot = FK(Depot)
    produit = FK(Produit)
    quantite = DecimalField  # positif = ajout, négatif = retrait
    motif = TextField  # obligatoire
    Statut = (en_attente / approuve / refuse)
    demande_par = FK(User)
    traite_par = FK(User, null=True)
```

**Endpoints** :
- CRUD `/inventaires/`
- POST `/inventaires/{id}/valider/` → superviseur valide → crée MouvementStock de correction
- CRUD `/ajustements-stock/`
- POST `/ajustements-stock/{id}/approuver/` — rôle superviseur+
- POST `/ajustements-stock/{id}/refuser/`

---

## Sprint 7 — Fournisseurs : Commandes + Dettes *(Jour 7)*
> §3.4

**Nouveaux modèles dans `apps/produits/models.py`** :
```python
class CommandeFournisseur(models.Model):
    company = FK(Company)
    fournisseur = FK(Fournisseur)
    numero = CharField  # CDF-YYYYMM-NNNN
    Statut = (brouillon / envoyee / partiellement_recue / recue / annulee)
    date_livraison_prevue = DateField
    created_par = FK(User)

class LigneCommandeFournisseur(models.Model):
    commande = FK(CommandeFournisseur)
    produit = FK(Produit)
    quantite_commandee = DecimalField
    prix_unitaire = DecimalField
    quantite_recue = DecimalField(default=0)

class MouvementDetteFournisseur(models.Model):
    fournisseur = FK(Fournisseur)
    TypeMouvement = (dette_ajoutee / paiement_effectue / avance)
    montant = DecimalField
    reference = CharField
    created_par = FK(User)
    created_at = DateTimeField
```

**Endpoints** :
- CRUD `/commandes-fournisseurs/`
- POST `/commandes-fournisseurs/{id}/recevoir/` → crée entree_stock + met à jour dette
- CRUD `/mouvements-dette/{fournisseur_id}/`

---

## Sprint 8 — Ventes : Retours + Devis *(Jour 8)*
> §3.5

**Nouveaux modèles dans `apps/ventes/models.py`** :
```python
class Devis(models.Model):
    company = FK(Company)
    numero = CharField  # DEV-YYYYMM-NNNN
    client = FK(Client)
    depot = FK(Depot)
    Statut = (brouillon / envoye / accepte / refuse / expire / converti)
    date_expiration = DateField
    commande = OneToOne(Commande, null=True)  # après conversion

class LigneDevis(models.Model):
    devis = FK(Devis)
    produit = FK(Produit)
    quantite = DecimalField
    prix_unitaire_ht = DecimalField

class RetourCommande(models.Model):
    commande = FK(Commande)
    Motif = (produit_defectueux / erreur_livraison / insatisfaction / autre)
    TypeRetour = (remboursement_especes / avoir / echange)
    montant_rembourse = DecimalField
    traite_par = FK(User)
    created_at = DateTimeField

class LigneRetour(models.Model):
    retour = FK(RetourCommande)
    produit = FK(Produit)
    quantite = DecimalField
    motif_ligne = TextField
```

**Endpoints** :
- CRUD `/devis/`
- POST `/devis/{id}/convertir/` → crée Commande depuis Devis
- CRUD `/retours/`
- POST `/retours/{id}/traiter/` → remboursement + retour en stock

**Historique points fidélité** :
- Ajouter modèle `HistoriquePoints` (client, type, points, commande FK null=True, created_at)
- Alimenté dans `creer_commande()` existant

---

## Sprint 9 — Logistique : Maintenance + Pannes *(Jour 9)*
> §3.7

**Nouveaux modèles dans `apps/logistique/models.py`** :
```python
class Maintenance(models.Model):
    vehicule = FK(Vehicule)
    TypeMaintenance = (preventive / corrective)
    description = TextField
    kilometrage_au_moment = IntegerField
    cout = DecimalField
    Statut = (planifiee / en_cours / terminee)
    date_planifiee = DateField
    date_reelle = DateField(null=True)
    effectue_par = FK(User)  # maintenancier

class Panne(models.Model):
    vehicule = FK(Vehicule)
    description = TextField
    date_declaration = DateTimeField
    mission = FK(Mission, null=True)  # si panne pendant mission
    cout_reparation = DecimalField(null=True)
    Statut = (declaree / en_reparation / resolue)
    declare_par = FK(User)

class DocumentVehicule(models.Model):
    vehicule = FK(Vehicule)
    TypeDocument = (assurance / visite_technique / carte_grise / autre)
    fichier = FileField
    date_expiration = DateField
    is_expire = property
```

**Endpoints** :
- CRUD `/maintenances/`
- CRUD `/pannes/`
- POST `/pannes/{id}/resoudre/`
- CRUD `/documents-vehicule/`

---

## Sprint 10 — RH : Historique affectations *(Jour 9, léger)*
> §3.10

**Nouveau modèle dans `apps/rh/models.py`** :
```python
class HistoriqueAffectation(models.Model):
    employe = FK(Employe)
    depot_ancien = FK(Depot, null=True)
    depot_nouveau = FK(Depot)
    motif = TextField
    effectue_par = FK(User)
    created_at = DateTimeField
```

- Signal `pre_save` sur `Employe` → si `depot` change → créer `HistoriqueAffectation`
- Endpoint `GET /employes/{id}/affectations/`

---

## Sprint 11 — Nettoyage + makemigrations globales *(Jour 10)*

1. Lancer `makemigrations` pour toutes les apps modifiées dans les sprints précédents
2. Vérifier `flake8 .` et `isort --check-only .`
3. Étendre `connect_audit_signals()` dans `accounts/apps.py` pour couvrir les nouveaux modèles
4. Mettre à jour le seed si nécessaire (ex: créer CaisseEntreprise + CaisseZone pour la company demo)
5. Supprimer les apps orphelines `apps/entreprises/` et `apps/zones/` (résidus d'ancienne archi)

---

## Sprint 12 — Tests *(Jour 11–12)*

> Les `tests.py` de toutes les apps hors `accounts` sont vides. Priorité aux flows critiques.

| App | Tests prioritaires |
|-----|--------------------|
| `stocks` | entree_stock, sortie_stock insuffisant, transfert complet, inventaire+ajustement |
| `ventes` | creer_commande, points fidélité, retour commande |
| `finance` | ouverture/fermeture session, écart + motif, versement inter-niveaux |
| `logistique` | workflow mission complet, scan QR, litige arrivée |
| `produits` | commande fournisseur, réception → entree_stock |

---

## Sprint 13 — Livrables finaux *(Jour 13–14)*

Selon le CDC §8, les livrables attendus sont :
- [ ] Code source versionné sur Git
- [ ] Script migration + données de test (fixtures ou seed étendu)
- [ ] Documentation API Swagger → déjà disponible via drf-spectacular
- [ ] Manuel utilisateur par rôle
- [ ] Rapport de projet : analyse, UML/ERD, bilan

---

## Récapitulatif des nouveaux modèles à créer

| App | Nouveaux modèles |
|-----|-----------------|
| `finance` | `CaisseZone`, `CaisseEntreprise`, `VersementCaisse` |
| `logistique` | `Maintenance`, `Panne`, `DocumentVehicule` |
| `stocks` | `Inventaire`, `LigneInventaire`, `AjustementStock` |
| `ventes` | `Devis`, `LigneDevis`, `RetourCommande`, `LigneRetour`, `HistoriquePoints` |
| `produits` | `CommandeFournisseur`, `LigneCommandeFournisseur`, `MouvementDetteFournisseur` |
| `rh` | `HistoriqueAffectation` |
| `accounts` ou `notifications` | `Notification` |

## Récapitulatif des champs à ajouter sur modèles existants

| Modèle | Champs à ajouter |
|--------|-----------------|
| `Vehicule` | `marque`, `modele`, `annee`, `capacite_charge_kg`, `kilometrage_actuel` |
| `Mission` | `qr_code` (UUID auto) |
| `CaissePhysique` | `devise` (default GNF) |
| `Categorie` | `tva_taux` (DecimalField, default 0) |
| `Document` (rh) | `commande` FK, `mission` FK, `transfert` FK (tous null=True) |
| `MouvementStock` | `fournisseur` FK null=True |

## Ce qui reste hors scope sprint (optionnel CDC)

- Variantes produits (§3.2)
- Prix différenciés par zone (§3.2)
- Import/export CSV catalogue (§3.2)
- Messagerie interne (§4.3)
- Mode automatique transferts avec Celery (§3.9)
- Facturation/abonnement SaaS (§3.15)
- Permissions granulaires affinables (§3.11)
- NFC véhicules (§5.1 — optionnel explicite)
- Scan code-barres (§5.2 — optionnel)
- IA prévisions (§5.3 — optionnel)
- 2FA (§5.4 — optionnel)
- Cartographie avancée polygones (§5.5 — optionnel)
