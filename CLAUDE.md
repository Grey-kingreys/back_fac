# DjoulaGest — Mémoire Backend

**Dernière mise à jour :** 19/06/2026 — Suppression utilisateurs (tombstone) + audit migrations  
**État CI :** ✅ Toutes les migrations sont générées et commitées · 142 tests accounts + tests Sprint 12 écrits  
**Deadline projet :** 20/06/2026 — **1 jour restant**

---

## ✅ Migrations — toutes générées et commitées

> **Rien à générer.** Tous les changements de modèles ont déjà leur fichier de migration commité.
> Le déploiement applique `migrate` **automatiquement** au démarrage ([docker/entrypoint.sh](docker/entrypoint.sh)
> étape 3 — `makemigrations` n'est exécuté qu'en dev si `RUN_MAKEMIGRATIONS=true`).
> Donc : écrire/commiter un fichier de migration suffit, le déploiement l'applique seul.

| App | Dernière(s) migration(s) | Couvre |
|-----|--------------------------|--------|
| `accounts` | `0007`, `0008`, `0009` | `zone` ; `first_login_done` ; **`is_deleted`+`deleted_at`+`deleted_by` (suppression tombstone)** |
| `finance` | `0005`, `0006` | `DepenseOperationnelle.is_deleted`+`deleted_at` ; `ConfigurationCaisse` |
| `stocks` | `0003` | `UniqueConstraint(company, numero)` sur `TransfertStock` + `Inventaire` |
| `ventes` | `0003` | `UniqueConstraint(company, numero)` sur `Commande` + `Devis` |
| `logistique` | `0006` | `UniqueConstraint(company, numero)` sur `Mission` |
| `produits` | `0003` | `UniqueConstraint(company, numero)` sur `CommandeFournisseur` |
| `companies` | `0006` | codes uniques par company/zone |

---

## ⚠️ Environnement de développement — IMPORTANT

**Pas de Python/pip installé en local.** Toutes les commandes Python (`isort`, `flake8`, `pytest`, `manage.py`, etc.) doivent être exécutées **via Docker** :

```bash
# Depuis d:\Souleymane\projet_fac\gestion_multi_sites\codes\backend\
docker compose exec backend isort --check-only --diff .
docker compose exec backend flake8 .
docker compose exec backend python manage.py migrate
docker compose exec backend pytest
```

Ne jamais utiliser `pip`, `python`, `isort`, `flake8` directement en local — ils ne sont pas disponibles.

---

## Démarrage rapide

```bash
cd backend
docker compose up --build
# API dispo sur http://localhost:8001
# Swagger : http://localhost:8001/api/schema/docs/
# ReDoc   : http://localhost:8001/api/schema/redoc/
```

L'`entrypoint.sh` exécute automatiquement : wait postgres → migrate → collectstatic → createsuperuser → seed_demo_data → gunicorn.

---

## Apps enregistrées dans INSTALLED_APPS

```python
LOCAL_APPS = [
    'apps.companies',       # ✅ CRUD + dashboard dépôt + analytics + dashboard superadmin
    'apps.accounts',        # ✅ complet
    'apps.produits',        # ✅ + CommandeFournisseur + MouvementDette + EvaluationFournisseur
    'apps.stocks',          # ✅ + Inventaire + AjustementStock + signal auto-mission
    'apps.ventes',          # ✅ + Devis + Retours + HistoriquePoints + Promotion + PDF
    'apps.finance',         # ✅ + Hiérarchie 4 niveaux + VersementCaisse + DepenseOperationnelle
    'apps.logistique',      # ✅ + QR + Maintenance + Panne + DocumentVehicule + ConsommationCarburant + PDF
    'apps.rh',              # ✅ + HistoriqueAffectation + signal + filtres docs avancés
    'apps.notifications',   # ✅ notifications in-app + 6 signaux automatiques
]
```

---

## Migrations (état post-sprint 13)

> ⚠️ Lancer `makemigrations` pour toutes les apps modifiées depuis la dernière migration.

```bash
python manage.py makemigrations companies produits stocks ventes finance logistique rh notifications
python manage.py migrate
```

| App | Nouvelles migrations |
|-----|----------------------|
| companies | 0004 — gestionnaire FK sur Depot |
| produits | 0002 — tva_taux Categorie + fournisseur FK MouvementStock + CommandeFournisseur + MouvementDette + EvaluationFournisseur |
| stocks | 0002 — Inventaire + LigneInventaire + AjustementStock |
| ventes | 0002 — HistoriquePoints + Devis + RetourCommande + LigneRetour + Promotion |
| finance | 0002 — devise CaissePhysique + CaisseZone + CaisseEntreprise + VersementCaisse + DepenseOperationnelle |
| logistique | 0004 — champs Vehicule + qr_code Mission + Maintenance + Panne + DocumentVehicule + ConsommationCarburant |
| rh | 0002 — commande/mission/transfert FK sur Document + HistoriqueAffectation |
| notifications | 0001 — Notification |
| accounts | 0006 — `two_factor_enabled` + `two_factor_method` + `totp_secret` sur CustomUser (17/06/2026) |
| accounts | 0007 — `zone` FK null=True sur CustomUser (superviseur → zone) — **à générer** |
| finance | 0006 — `ConfigurationCaisse` (OneToOne company, duree_session/depot/zone_jours) — **écrite manuellement** |

---

## Endpoints API complets

Préfixe commun : `/api/`

### Auth (`apps/accounts/urls_auth.py`)
| Méthode | URL |
|---------|-----|
| POST | `/auth/login/` |
| POST | `/auth/refresh/` |
| POST | `/auth/logout/` |
| GET/PATCH | `/auth/me/` |
| POST | `/auth/me/change-password/` |
| POST | `/auth/password-reset/` |
| POST | `/auth/password-reset/confirm/` |
| GET/POST | `/auth/first-login/` |
| POST | `/auth/2fa/setup/` | IsAuthenticated — method='totp' → QR base64 + secret ; method='email' → envoie OTP |
| POST | `/auth/2fa/setup-verify/` | IsAuthenticated — vérifie code, active 2FA sur le user |
| POST | `/auth/2fa/disable/` | IsAuthenticated — désactive 2FA (requiert password) |
| POST | `/auth/2fa/login-verify/` | AllowAny — temp_token + code → access + refresh + user |
| POST | `/auth/2fa/resend/` | AllowAny — renvoie OTP email (méthode email uniquement) |

### Users & Audit
| Méthode | URL |
|---------|-----|
| GET/POST | `/users/` |
| GET/PATCH | `/users/{id}/` |
| DELETE | `/users/{id}/` — **Désactiver** (soft, `is_active=False`, réactivable via PATCH) |
| DELETE | `/users/{id}/supprimer/` — **Supprimer** : purge si aucun historique, sinon archivage tombstone (`is_deleted=True`, retiré des listes, nom+email conservés sur l'historique). Migration `accounts/0009`. |
| POST | `/users/{id}/reset-password/` |
| GET | `/audit-logs/` |
| GET | `/login-logs/` |

> **Corrections 19/06 (sans migration) :**
> - **Audit acteur** : `AuditMiddleware` lisait `request.user` AVANT la vue → avec JWT/DRF (auth dans la vue) tous les logs avaient `user=None` → l'admin (filtré par sa société) ne voyait rien. Corrigé : `set_audit_context(request=...)` + `get_current_user()` lit `request.user` **paresseusement** au moment du signal (`signals.py`, `middleware.py`). L'admin voit maintenant ses propres actions.
> - **Caisse Entreprise auto-créée** : `CompanyCreateSerializer.create` crée désormais une `CaisseEntreprise` (get_or_create) à la création d'entreprise → l'admin peut la configurer au 1er login.
> - **Véhicules** : `LOG_WRITE_VEHICLE = [ADMIN, MAINTENANCIER]`.

### Companies, Zones, Dépôts
| Méthode | URL | Note |
|---------|-----|------|
| GET/POST | `/companies/` | SuperAdmin only |
| GET/PATCH | `/companies/{id}/` | |
| POST | `/companies/{id}/toggle/` | |
| GET/POST/PATCH/DELETE | `/zones/` | |
| GET/POST/PATCH/DELETE | `/depots/` | champ gestionnaire inclus |
| GET | `/depots/{id}/dashboard/` | ✅ données réelles |
| GET | `/superadmin/dashboard/` | ✅ agrégat toutes companies (SuperAdmin) |
| GET | `/analytics/ventes/` | |
| GET | `/analytics/stock/` | |
| GET | `/analytics/finance/` | |
| GET | `/analytics/tva/` | |
| GET | `/analytics/performance/` | |

### Produits
| Méthode | URL |
|---------|-----|
| CRUD | `/categories/` |
| CRUD | `/unites/` |
| CRUD | `/fournisseurs/` |
| GET | `/fournisseurs/{id}/evaluations/` |
| CRUD | `/produits/` |
| GET | `/produits/{id}/stock/` |
| CRUD | `/commandes-fournisseurs/` |
| POST | `/commandes-fournisseurs/{id}/recevoir/` |
| GET/POST | `/mouvements-dette/` |
| CRUD | `/evaluations-fournisseurs/` |

### Stocks
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
| CRUD | `/inventaires/` |
| POST | `/inventaires/{id}/valider/` |
| CRUD | `/ajustements-stock/` |
| POST | `/ajustements-stock/{id}/approuver/` |
| POST | `/ajustements-stock/{id}/refuser/` |

### Ventes
| Méthode | URL |
|---------|-----|
| CRUD | `/clients/` |
| GET | `/clients/creances/` | Clients avec solde > 0 |
| GET/POST | `/commandes/` |
| GET | `/commandes/{id}/` |
| POST | `/commandes/{id}/paiement/` |
| POST | `/commandes/{id}/annuler/` |
| GET | `/commandes/{id}/facture/` | PDF reportlab |
| GET | `/commandes/{id}/bon-livraison/` | PDF reportlab |
| GET/PATCH | `/fidelite/parametres/` |
| CRUD | `/devis/` |
| POST | `/devis/{id}/convertir/` |
| CRUD | `/retours/` |
| GET | `/historique-points/` |
| CRUD | `/promotions/` | Remises par produit/client/période |

### Finance
| Méthode | URL |
|---------|-----|
| CRUD | `/taux-change/` |
| CRUD | `/caisses/` | CaissePhysique niveau dépôt |
| CRUD | `/caisses-zone/` | CaisseZone niveau zone |
| GET/PATCH | `/caisse-entreprise/` | CaisseEntreprise (OneToOne) |
| GET | `/caisses/consolidation/` | Soldes tous niveaux agrégés |
| GET | `/sessions-caisse/` |
| POST | `/sessions-caisse/ouvrir/` |
| POST | `/sessions-caisse/{id}/fermer/` |
| POST | `/sessions-caisse/{id}/transaction/` |
| POST | `/versements-caisse/` | Versement inter-niveaux |
| GET/PATCH | `/configuration-caisses/` |
| CRUD | `/comptes-mobile-money/` |
| POST | `/comptes-mobile-money/{id}/transaction/` |
| GET | `/comptes-mobile-money/{id}/transactions/` |
| CRUD | `/depenses/` | DepenseOperationnelle (carburant, maintenance, salaires…) |

### Logistique
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
| GET | `/missions/{id}/qr/` | Image QR base64 |
| POST | `/missions/scanner-qr/` | Scan → PLANIFIEE→CHARGEMENT |
| GET | `/missions/{id}/bon-livraison/` | PDF signé |
| CRUD | `/maintenances/` |
| CRUD | `/pannes/` |
| POST | `/pannes/{id}/resoudre/` |
| CRUD | `/documents-vehicule/` |
| CRUD | `/carburant/` | ConsommationCarburant — met à jour km véhicule |

### RH
| Méthode | URL |
|---------|-----|
| CRUD | `/employes/` |
| GET | `/employes/{id}/presences/` |
| GET | `/employes/{id}/conges/` |
| GET | `/employes/{id}/documents/` |
| GET | `/employes/{id}/affectations/` |
| CRUD | `/presences/` |
| CRUD | `/conges/` |
| POST | `/conges/{id}/approuver/` |
| POST | `/conges/{id}/refuser/` |
| CRUD | `/documents/` | Filtres: type, employe, commande, mission, transfert, search, date |
| CRUD | `/objectifs-vente/` |

### Notifications
| Méthode | URL |
|---------|-----|
| GET | `/notifications/` |
| POST | `/notifications/{id}/lire/` |
| POST | `/notifications/tout-lire/` |

---

## Modèles existants (état final)

### apps.companies
- `Company` : name, slug, logo, is_active, subscription_plan, settings
- `Zone` : company, name, code, latitude, longitude, is_active
- `Depot` : zone, name, code, address, is_active, **gestionnaire** FK User null=True

### apps.produits
- `Categorie` : company, name, couleur, **tva_taux** (default 0), is_active
- `Unite` : company, name, symbole
- `Fournisseur` : company, code, nom, solde_dette, is_active
- `Produit` : company, categorie, unite, fournisseur_principal, reference, prix_achat/vente, seuil_alerte/max, est_perimable, tva_taux
- `CommandeFournisseur` : company, fournisseur, numero `CDF-YYYYMM-NNNN`, Statut, depot_destination, created_par
- `LigneCommandeFournisseur` : commande, produit, quantite_commandee, prix_unitaire, quantite_recue
- `MouvementDetteFournisseur` : fournisseur, TypeMouvement, montant, reference, created_par
- `EvaluationFournisseur` : fournisseur, commande null=True, note_qualite/delai/service (1→5), commentaire, evalue_par, `note_globale` property

### apps.stocks
- `StockDepot` : depot + produit (unique_together), quantite, `en_alerte` property
- `LotStock` : stock_depot, numero_lot, quantite, date_expiration
- `MouvementStock` : TypeMouvement (entree/sortie/transfert/inventaire/ajustement), fournisseur FK null=True
- `TransfertStock` : auto `TRF-YYYYMM-NNNN`, Statut — **signal post_save : auto-crée Mission si EN_TRANSIT**
- `LigneTransfert` : transfert, produit, quantite_envoyee, quantite_recue
- `Inventaire` : company, depot, numero `INV-YYYYMM-NNNN`, Statut, cree_par, valide_par
- `LigneInventaire` : inventaire, produit, quantite_theorique, quantite_comptee, `ecart` property
- `AjustementStock` : company, depot, produit, quantite (±), motif, Statut, demande_par, traite_par

### apps.ventes
- `ParametresFidelite` : company (OneToOne), tranche_montant, points_par_tranche, valeur_point_gnf
- `Client` : company, code, points_fidelite, solde_credit
- `Commande` : auto `CMD-YYYYMM-NNNNN`, Statut, remise, `reste_a_payer`, `est_solde`
- `LigneCommande` : produit, quantite, prix_unitaire_ht, tva_taux, montant_ht/tva/ttc
- `Paiement` : Mode (especes/orange_money/mtn_money/virement/points_fidelite)
- `HistoriquePoints` : client, TypeMouvement (gain/utilisation/annulation), points, commande null=True
- `Devis` : company, client, depot, numero `DEV-YYYYMM-NNNN`, Statut, commande OneToOne null=True
- `LigneDevis` : devis, produit, quantite, prix_unitaire_ht, `montant_ht` property
- `RetourCommande` : commande, Motif, TypeRetour, montant_rembourse, traite_par
- `LigneRetour` : retour, produit, quantite, motif_ligne
- `Promotion` : company, nom, TypePromotion (pourcentage/montant_fixe/prix_special), Cible (tous/client/categorie), produit FK null=True, date_debut/fin, `est_active_aujourd_hui()` method

### apps.finance

- `ConfigurationCaisse` : company (OneToOne), duree_session_jours (default 1), duree_caisse_depot_jours (default 30), duree_caisse_zone_jours (default 90), updated_at, updated_by FK User — `clean()` enforce `session < depot < zone`
- `TauxChange` : company, devise_source, devise_cible, taux, date_expiration, `est_expire` property
- `CaissePhysique` : company, depot (OneToOne), devise (default GNF), solde_actuel — niveau dépôt
- `CaisseZone` : company, zone (OneToOne), devise, solde_actuel — niveau zone
- `CaisseEntreprise` : company (OneToOne), devise, solde_actuel — niveau entreprise
- `VersementCaisse` : TypeVersement (depot_vers_zone/zone_vers_entreprise), montant, justificatif, montant_comptage_receveur, `ecart` property
- `SessionCaisse` : caisse, caissier, Statut OUVERTE/FERMEE, motif_ecart
- `TransactionCaisse` : TypeTransaction, montant, reference_doc
- `CompteMobileMoney` : Operateur (orange_money/mtn_money), company, depot
- `TransactionMobileMoney` : TypeTransaction, montant, reference_operateur
- `DepenseOperationnelle` : company, depot null=True, Categorie (carburant/maintenance/salaires/loyer/fournitures/transport/autre), montant, justificatif, session_caisse null=True

### apps.logistique
- `Vehicule` : company, immatriculation, type, marque, modele, annee, capacite_kg, kilometrage_actuel, Statut, has_nfc
- `Mission` : auto `MSN-YYYYMM-NNNN`, **qr_code UUID auto**, 7 Statuts, signature_arrivee (base64), transfert_stock OneToOne null=True
- `LigneMission` : mission, produit, quantite, quantite_recue
- `PositionGPS` : mission, latitude, longitude, vitesse_kmh
- `Maintenance` : vehicule, TypeMaintenance (preventive/corrective), Statut (planifiee/en_cours/terminee), cout, date_planifiee/reelle
- `Panne` : vehicule, description, mission null=True, cout_reparation, Statut, resolu_le
- `DocumentVehicule` : vehicule, TypeDocument (assurance/visite_technique/carte_grise/autre), date_expiration, `is_expire` property
- `ConsommationCarburant` : vehicule, mission null=True, TypeCarburant, quantite_litres, prix_par_litre, kilometrage, date_plein, `montant_total` property — **met à jour kilometrage_actuel du Vehicule à la création**

### apps.rh
- `Employe` : company, user null=True, depot, matricule, salaire_base, Statut
- `Presence` : employe + date (unique_together), TypePresence
- `Conge` : TypeConge, Statut, `nb_jours` property
- `Document` : company, type, fichier, employe null=True, **commande null=True, mission null=True, transfert null=True** — filtres avancés sur le ViewSet
- `ObjectifVente` : depot + annee + mois (unique_together), `taux_realisation` property
- `HistoriqueAffectation` : employe, depot_ancien/nouveau, motif — alimenté par signal `pre_save` sur Employe

### apps.notifications
- `Notification` : destinataire, company, TypeNotification (11 types), titre, message, lien, est_lue

**Signaux automatiques :**
| Signal | Déclencheur | Résultat |
|--------|-------------|---------|
| `notifier_seuil_stock` | StockDepot post_save en_alerte=True | → Notification gestionnaire_stock + admin |
| `notifier_ecart_caisse` | SessionCaisse post_save statut=FERMEE avec motif_ecart | → Notification admin + superviseur |
| `notifier_mission_litige` | Mission post_save statut=LITIGE | → Notification admin + superviseur |
| `notifier_transfert_receptionne` | TransfertStock post_save statut=RECU | → Notification admin + gestionnaire_stock |
| `notifier_conge_approuve` | Conge post_save statut=APPROUVE | → Notification employé |
| `notifier_seuil_fidelite` | Client post_save points atteint seuil | → Notification caissier + admin |
| `creer_mission_sur_transit` | TransfertStock post_save statut=EN_TRANSIT | → Mission auto-créée si véhicule disponible |

---

## Architecture de sécurité multi-tenant

- **Pattern 1 — FK directe** (`company = FK(Company)`) → `CompanyFilterMixin`
- **Pattern 2 — FK indirecte** → override manuel `get_queryset()`

**Pattern 1 :** Categorie, Unite, Fournisseur, Produit, TransfertStock, Client, TauxChange, CaissePhysique, CaisseZone, CaisseEntreprise, CompteMobileMoney, Vehicule, Employe, Document, ObjectifVente, CommandeFournisseur, Inventaire, AjustementStock, Devis, Promotion, DepenseOperationnelle, Notification

**Pattern 2 :** StockDepot, MouvementStock, Commande, SessionCaisse, TransactionCaisse, TransactionMobileMoney, Mission, PositionGPS, Presence, Conge, Maintenance, Panne, DocumentVehicule, ConsommationCarburant, HistoriqueAffectation

---

## Services métier

### `apps/stocks/services.py`
- `entree_stock()` — crée LotStock si périmable, met à jour StockDepot, écrit MouvementStock
- `sortie_stock()` — FEFO, ValidationError si insuffisant
- `creer_transfert()`, `expedier_transfert()`, `receptionner_transfert()`

### `apps/ventes/services.py`
- `creer_commande()` — transaction atomique : stock, commande, sortie_stock, fidélité, paiement initial, **HistoriquePoints alimenté**

---

## Conventions de code

### Isort — sections personnalisées (setup.cfg)
`FUTURE → STDLIB → DJANGO → THIRDPARTY → FIRSTPARTY → LOCALFOLDER`

### flake8 — ignorés globalement
`E501`, `F401`, `W503/W504`

### Commentaires de section `# ──`
0 ligne vide entre commentaire et classe. 2 lignes vides avant le commentaire.

### Format de réponse API
- `companies` : enveloppe `{success, data, message}`
- Toutes les autres apps : format DRF standard

---

## Observabilité (LGTM stack)

Entièrement **commenté** dans `docker-compose.yml`. OTel installé. Pour activer, créer les répertoires de config et décommenter les services.

---

## CI (`backend/.github/workflows/backend-ci.yml`)

1. `pip install -r requirements.txt`
2. `flake8 .`
3. `isort --check-only .`
4. `python manage.py migrate`
5. `pytest || [ $? -eq 5 ]`

**État actuel :** 142 tests accounts passent + tests Sprint 12 écrits (stocks, ventes, finance, logistique, produits).

---

## Données de démo (seed étendu)

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

**Données supplémentaires créées au démarrage :**
- CaisseEntreprise + CaisseZone (Conakry/Kindia/Labé) + CaissePhysique par dépôt
- ParametresFidelite (10 000 GNF = 1 point, 1 point = 100 GNF)
- 3 clients démo (CLT-001, CLT-002, CLT-003)
- 2 produits démo (PROD-001 Riz, PROD-002 Huile)

---

## Fichiers de configuration clés

| Fichier | Rôle |
|---------|------|
| `config/settings.py` | Django, JWT, Redis, CORS, INSTALLED_APPS |
| `config/urls.py` | Routes racine `/api/` |
| `docker-compose.yml` | web, postgres, redis + LGTM commenté |
| `entrypoint.sh` | migrate → seed → gunicorn |
| `setup.cfg` | flake8 + isort (profile black) |
| `requirements.txt` | Django 5.x, DRF 3.15, SimpleJWT, drf-spectacular, reportlab, qrcode[pil], openpyxl |

---

## Corrections permissions superadmin (17/06/2026) — Audit skill gestion-multisites

**Problème :** `HasRole.has_permission()` bypassait le superadmin (`if user.is_superadmin: return True`), lui donnant accès à TOUS les endpoints opérationnels (zones, dépôts, users, produits, stocks, finance, ventes, logistique, RH) — violation du CDC.

**Règle CDC :** Le superadmin gère la plateforme (companies, activation, facturation, dashboard agrégé). Il ne peut PAS accéder aux opérations internes des entreprises.

| Fichier | Correction |
|---------|-----------|
| `apps/accounts/permissions.py` | Supprimé le bypass superadmin dans `HasRole.has_permission()` + ajout classe `IsSuperAdminBlocked` |
| `apps/companies/views.py` | `IsSuperAdminBlocked()` ajouté en premier dans `CompanyObjectMixin.get_permissions()` |
| `apps/accounts/views_users.py` | `IsSuperAdminBlocked()` ajouté en premier dans `UserViewSet.get_permissions()` |
| `apps/accounts/tests/test_zones_depots.py` | 2 tests mis à jour → assertent 403 pour superadmin |
| `apps/accounts/tests/test_users.py` | 1 test mis à jour → asserte 403 pour superadmin |
| `apps/accounts/tests/test_permissions.py` | `test_superadmin_bloque_si_role_absent` → asserte False (HasRole sans bypass) |
| `apps/accounts/test_permissions.py` | Même correction (style TestCase) |
| `apps/produits/tests/test_produits.py` | `test_superadmin_refuse_produits` → asserte 403 |

**Endpoints superadmin TOUJOURS accessibles (non affectés) :**

- `GET/POST /api/companies/` — vérifie `role == SUPERADMIN` manuellement
- `GET/PATCH /api/companies/{id}/` — idem
- `POST /api/companies/{id}/toggle/` — idem
- `GET /api/superadmin/dashboard/` — idem

---

## Bugs de serializers corrigés (17/06/2026) — Audit cross-platform mobile/backend

> **Contexte :** Les modèles `Zone` et `Depot` utilisent des noms de champs en **anglais** (`name`, `code`), mais 11 champs `CharField(source=...)` pointaient vers `.nom` (français) — ce qui retournait silencieusement `None` côté DRF sans lever d'erreur. Symptôme observé : création de zone/dépôt impossible côté mobile sans aucun message d'erreur.

### Convention confirmée (source de vérité : `apps/companies/models.py`)
| Modèle | Champ nom | Convention |
|--------|-----------|------------|
| `Company` | `name` | Anglais |
| `Zone` | `name`, `code` | Anglais |
| `Depot` | `name`, `code` | Anglais |
| `CaissePhysique` | `nom` | Français ← CORRECT |
| `CaisseZone` | `nom` | Français ← CORRECT |
| `Produit` | `nom` | Français ← CORRECT |
| `Fournisseur` | `nom` | Français ← CORRECT |
| `Employe` | `nom`, `prenom` | Français ← CORRECT |

### Corrections appliquées (`source='.nom'` → `source='.name'`)

| Fichier | Serializer | Champ corrigé |
|---------|-----------|---------------|
| `apps/finance/serializers.py` L.40 | `CaissePhysiqueSerializer` | `depot_nom = CharField(source='depot.name')` |
| `apps/finance/serializers.py` L.117 | `CompteMobileMoneySerializer` | `depot_nom = CharField(source='depot.name')` |
| `apps/finance/serializers.py` L.153 | `CaisseZoneSerializer` | `zone_nom = CharField(source='zone.name')` |
| `apps/finance/serializers.py` L.201 | `DepenseOperationnelleSerializer` | `depot_nom = CharField(source='depot.name', allow_null=True)` |
| `apps/logistique/serializers.py` | `MissionListSerializer` | `depot_depart_nom`, `depot_arrivee_nom` → `.name` |
| `apps/logistique/serializers.py` | `MissionDetailSerializer` | `depot_depart_nom`, `depot_arrivee_nom` → `.name` |
| `apps/rh/serializers.py` | `EmployeListSerializer`, `EmployeDetailSerializer`, `ObjectifVenteSerializer` | `depot_nom = CharField(source='depot.name')` |
| `apps/stocks/serializers.py` L.222 | `InventaireDetailSerializer` | `depot_nom = CharField(source='depot.name')` |
| `apps/produits/serializers.py` L.196 | `CommandeFournisseurDetailSerializer` | `depot_nom = CharField(source='depot_destination.name')` |

> ⚠️ **Règle à respecter :** Toujours vérifier `apps/companies/models.py` avant d'écrire un `source=` sur un champ de Zone ou Depot. Ces modèles sont en anglais. Les autres modèles métier (Produit, Fournisseur, Employe, Caisse*) sont en français.

---

## Corrections + features (18/06/2026) — Session 3 (audit cross-platform mobile/backend)

### Superviseur → Zone (accounts)

`UserCreateSerializer` et `UserUpdateSerializer` : ajout `zone_id` (FK vers Zone, source=`zone`).  
Règle enforce dans `validate()` : si `role == SUPERVISEUR` → `zone` obligatoire, `depot` effacé ; sinon `zone` effacé.  
`UserListSerializer` et `UserDetailSerializer` : ajout champs `zone_id` + `zone_name`.  
Email : validation globale (pas scoped company) pour éviter IntegrityError 500.

### ConfigurationCaisse (finance)

Nouveau modèle `ConfigurationCaisse` (OneToOne company) avec `duree_session_jours`, `duree_caisse_depot_jours`, `duree_caisse_zone_jours`.  
`clean()` enforce `session < depot < zone`. Vue `ConfigurationCaisseView` (GET/PATCH). Route `/configuration-caisses/`.  
Migration `finance/0006_configurationcaisse.py` écrite manuellement (pas de Python local).

### Bugs corrigés

| Fichier | Bug | Correction |
| ------- | --- | ---------- |
| `notifications/signals.py` | Anti-dedup filtre sur `type_notification='seuil_stock'` alors que notif créée avec `type='info'` → spam infini | Filtre changé en `type_notification='info'` |
| `produits/views.py` | `MouvementDetteFournisseur.create()` — pas de vérif company fournisseur → cross-tenant possible | Check `fournisseur.company_id != request.user.company_id` |
| `logistique/views.py` | `ConsommationCarburant.create()` — pas de vérif company véhicule/mission → cross-tenant possible | Check company vehicule + mission |
| `companies/views.py` | `DepotViewSet.get_queryset()` — résidu `if user.is_superadmin: return qs` (dangereux même si IsSuperAdminBlocked en amont) | Supprimé |
| `ventes/views.py` | `convertir` — condition morte `if devis.statut == ANNULE if hasattr(...) else False` → jamais True | Corrigé en `if devis.statut == EXPIRE: raise ValidationError(...)` |
| `finance/serializers.py` | `VersementCaisseSerializer` — `motif_ecart` non requis même quand écart ≠ 0 | Validate : `motif_ecart` obligatoire si `montant_comptage_receveur != montant` |

---

## Corrections audit complet backend (17/06/2026)

| # | Fichier(s) | Correction |
|---|-----------|-----------|
| E1 | `companies/models.py` + migration `0006` | `Zone.code` et `Depot.code` : `unique=True` global → `UniqueConstraint` scoped par company/zone — isolation SaaS |
| E2 | `accounts/permissions.py` | `BaseCompanyPermission.has_permission()` : supprimé `if user.is_superadmin: return True` |
| S5+V3+V5 | `accounts/permissions.py` | `CompanyFilterMixin` + `DepotFilterMixin` : ajout `check_permissions()` qui bloque le superadmin + suppression `if user.is_superadmin: return queryset` dans `get_queryset()` |
| V1 | Tous les fichiers `views.py` (7 apps) | `IsSuperAdminBlocked` importé + ajouté dans **chaque** `get_permissions()` pour défense en profondeur |
| — | `accounts/permissions.py` | `IsSupervisorOrAbove` : supprimé `Role.SUPERADMIN` des `allowed_roles` |
| E3+S4 | `ventes/serializers.py` | `PaiementInputSerializer.validate()` + `CommandeCreateSerializer.validate()` : référence obligatoire pour Orange Money, MTN Money, Virement |
| V4 | `finance/views.py` | `VersementCaisseViewSet.create()` : vérification que toutes les caisses appartiennent à la company de l'utilisateur |
| S3 | `logistique/serializers.py` + `views.py` | `MissionCreateSerializer` : ajout champ `type_mission` + passé à `Mission.objects.create()` |
| CI1 | `.github/workflows/backend-ci.yml` | Job lint : `pip install flake8 isort` → `pip install -r requirements.txt` (isort lit `setup.cfg`) |
| CI2 | `.github/workflows/backend-ci.yml` | `RESEND_KEY` ajouté dans les 3 étapes env du job test |
| U1 | `CLAUDE.md` | URL Swagger corrigée : `/api/schema/swagger-ui/` → `/api/schema/docs/` |

---

---

# ANALYSE DES ÉCARTS CDC — État final 07/06/2026

> Légende : ✅ Implémenté · ⚠️ Partiel · ❌ Absent (hors scope ou optionnel)

## §3.1 Zones et Dépôts
| Exigence | État |
|----------|------|
| CRUD zones + GPS | ✅ |
| Dashboard par dépôt | ✅ |
| Dépôt → caisse physique | ✅ |
| Gestionnaire assigné au dépôt | ✅ |
| Transfert de responsabilité gestionnaires | ⚠️ Modèle présent (gestionnaire FK) — endpoint dédié non prioritaire |

## §3.2 Produits
| Exigence | État |
|----------|------|
| Fiche produit complète | ✅ |
| Alerte automatique seuil stock | ✅ Signal → Notification |
| FEFO périmables | ✅ |
| TVA par catégorie | ✅ |
| Prix différenciés par zone | ❌ Hors scope |
| Variantes produits | ❌ Hors scope |
| Import/export CSV | ❌ Hors scope |

## §3.3 Stocks
| Exigence | État |
|----------|------|
| Approvisionnement / entrée | ✅ |
| Transferts inter-dépôts | ✅ |
| Inventaires physiques | ✅ |
| Ajustements de stock | ✅ |
| FIFO/FEFO | ✅ |

## §3.4 Fournisseurs
| Exigence | État |
|----------|------|
| Fiche fournisseur | ✅ |
| Commandes fournisseurs | ✅ |
| Gestion avances et dettes | ✅ |
| Évaluation fournisseurs | ✅ EvaluationFournisseur |
| Historique achats | ⚠️ MouvementStock.fournisseur FK présent |

## §3.5 Ventes et Clients
| Exigence | État |
|----------|------|
| Fiches clients + commandes + paiements | ✅ |
| PDF factures + bons de livraison | ✅ reportlab |
| Retours clients | ✅ |
| Système devis → commande | ✅ |
| Historique points fidélité | ✅ |
| Suivi créances | ✅ `/clients/creances/` |
| Remises et promotions | ✅ Promotion (pourcentage/fixe/prix spécial) |
| Relances automatiques | ⚠️ Vue créances présente — emails automatiques hors scope |

## §3.6 Finance
| Exigence | État |
|----------|------|
| Hiérarchie 4 niveaux | ✅ CaisseEntreprise + CaisseZone + CaissePhysique + SessionCaisse |
| Jamais supprimée/réouverte | ✅ |
| Motif obligatoire pour écarts | ✅ |
| Versements inter-niveaux + double comptage | ✅ |
| Vue consolidée soldes | ✅ `/caisses/consolidation/` |
| Dépenses opérationnelles | ✅ DepenseOperationnelle |
| Devise par caisse | ✅ |
| Alerte taux de change expiré | ✅ Signal → Notification |
| Consolidation automatique à la fermeture | ⚠️ VersementCaisse existe mais pas de trigger auto |
| Hiérarchie Mobile Money (Zone/Entreprise) | ❌ Hors scope |

## §3.7 Logistique
| Exigence | État |
|----------|------|
| Fiche véhicule complète + km | ✅ |
| QR code + scan | ✅ |
| GPS tracking | ✅ |
| Signature HTML5 | ✅ |
| PDF bon de livraison signé | ✅ |
| Maintenance préventive/corrective | ✅ |
| Gestion pannes | ✅ |
| Documents véhicule + expiration | ✅ |
| Consommation carburant | ✅ ConsommationCarburant |
| Mission auto sur TransfertStock EN_TRANSIT | ✅ Signal |
| Statut Litige + notification | ✅ |
| Maintenance prédictive (alertes km) | ⚠️ Modèle présent — tâche Celery périodique hors scope |

## §3.8 Tableau de Bord Logistique
| Exigence | État |
|----------|------|
| Liste missions actives | ✅ |
| Historique GPS | ✅ |
| Alertes litige | ✅ |

## §3.9 Planification Transferts
| Exigence | État |
|----------|------|
| Mode manuel | ✅ |
| Notifications validation | ✅ |
| Mission auto sur transit | ✅ Signal |
| Mode automatique Celery | ❌ Hors scope |

## §3.10 RH
| Exigence | État |
|----------|------|
| Fiche employé, présences, congés | ✅ |
| Historique affectations | ✅ |
| Notifications congé approuvé | ✅ |

## §3.12 Fidélité
| Exigence | État |
|----------|------|
| Attribution + conversion points | ✅ |
| Configuration admin | ✅ |
| Historique points | ✅ |
| Notifications seuil atteint | ✅ Signal |

## §3.13 Gestion Documentaire
| Exigence | État |
|----------|------|
| Upload documents | ✅ |
| Rattachement Commande/Mission/Transfert | ✅ |
| Filtres avancés | ✅ type, employe, commande, mission, transfert, search, date |

## §3.14 TVA
| Exigence | État |
|----------|------|
| TVA par produit + HT/TTC | ✅ |
| TVA par catégorie | ✅ |
| Rapport TVA par période | ✅ `/analytics/tva/` |

## §3.15 SaaS Multi-Entreprise
| Exigence | État |
|----------|------|
| CRUD companies + isolation + toggle | ✅ |
| Dashboard analytique | ✅ 5 endpoints |
| Dashboard superadmin agrégé | ✅ `/superadmin/dashboard/` |
| Facturation/abonnement | ❌ Hors scope |

## §4 Transversales
| Exigence | État |
|----------|------|
| Dashboard analytique KPIs | ✅ |
| PDF rapports | ✅ |
| Notifications in-app | ✅ |
| Alertes automatiques | ✅ |
| Objectifs commerciaux | ✅ |
| Rapport performance | ✅ |
| API Swagger | ✅ |
| Messagerie interne | ❌ Hors scope |
| Export Excel | ⚠️ openpyxl installé — endpoints non implémentés |

---

---

# PLAN DE PROGRESSION — État final

## ✅ Sprint 1 — Corrections modèles existants
## ✅ Sprint 2 — Hiérarchie des caisses
## ✅ Sprint 3 — QR Code missions + PDF
## ✅ Sprint 4 — Dashboard dépôt + Analytics
## ✅ Sprint 5 — Notifications et Alertes
## ✅ Sprint 6 — Stocks : Inventaires + Ajustements
## ✅ Sprint 7 — Fournisseurs : Commandes + Dettes
## ✅ Sprint 8 — Ventes : Retours + Devis
## ✅ Sprint 9 — Logistique : Maintenance + Pannes
## ✅ Sprint 10 — RH : Historique affectations
## ✅ Sprint 11 — Nettoyage + intégration
## ✅ Sprint 12 — Tests (stocks, ventes, finance, logistique, produits)
## ✅ Sprint 13 — Livrables : seed étendu + CLAUDE.md complet

## Fonctionnalités optionnelles hors scope
- Variantes produits, prix par zone, import CSV
- Messagerie interne
- Mode automatique Celery pour transferts
- Hiérarchie Mobile Money Zone/Entreprise
- Facturation/abonnement SaaS
- Permissions granulaires affinables
- NFC véhicules, scan code-barres, IA, 2FA, cartographie avancée
