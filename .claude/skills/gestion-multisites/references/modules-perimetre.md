# Modules & Périmètre — Référence

## Table des matières

1. Périmètre fonctionnel (les 15 modules)
2. Fonctionnalités transversales
3. Cœur vs optionnel
4. Exigences non fonctionnelles
5. Stack technique
6. Contraintes & hypothèses

---

## 1. Périmètre fonctionnel (les 15 modules)

1. **Zones & Dépôts** — zones nommées avec point central GPS cliquable sur carte (OpenStreetMap),
   **rattachées à une entreprise** ; chaque zone regroupe plusieurs dépôts ; chaque **dépôt est
   rattaché à une zone (obligatoire) et possède SA propre géolocalisation**, un gestionnaire
   (responsable), une caisse physique, un ou plusieurs comptes mobile money ; transfert de
   responsabilité entre gestionnaires (historisé).
2. **Produits** — fiches (réf., catégorie, unité, description), prix achat/vente (différenciés par
   zone possible), seuils mini + alertes, variantes, import/export CSV/Excel, périmables (FEFO).
3. **Stocks & Mouvements** — appro avec bons de réception, transferts inter-dépôts traçables,
   inventaires avec écarts, ajustements (motif + validation superviseur), FIFO par défaut.
4. **Fournisseurs** — fiches, suivi commandes/livraisons, historique d'achats, avances/dettes,
   évaluation/comparaison (délais, qualité, coût).
5. **Ventes & Clients** — fiches clients, commandes (dépôt source), bons de livraison + factures
   PDF numérotées, paiements (comptant/partiel/crédit), créances + relances, retours, remises,
   devis→commande, TVA auto.
6. **Financier** — hiérarchie de caisses (4 niveaux), comptes mobile money, dépenses par catégorie,
   rapports (journal de caisse, recettes/dépenses, créances), alertes d'anomalies, multi-devises.
7. **Logistique (flotte & transport)** — fiches véhicules, **missions initiées par le gestionnaire
   du dépôt** et exécutées par un chauffeur (3 types : transfert inter-dépôt/zone, livraison client,
   enlèvement fournisseur — cf. regles-metier §0bis), assignation chauffeurs,
   kilométrage/carburant, maintenance préventive/corrective/prédictive, pannes, documents véhicule
   avec rappels, historique.
8. **Tableau de bord logistique** — carte temps réel des camions, missions actives, historique des
   trajets, alertes (arrêt prolongé, retard, perte GPS, litige).
9. **Planification des transferts de stock** — mode automatique (recommandations) / manuel ;
   notifications ; validation → mission logistique.
10. **Ressources humaines** — fiches employés, présences/absences, permissions/congés, historique
    des affectations (mutations).
11. **Utilisateurs & Rôles** — 7 rôles opérationnels + permissions granulaires, journal d'audit,
    blocage après tentatives échouées, journal de connexion.
12. **Fidélité client** — points configurables, conversion en réductions, notifications de seuil.
13. **Documentaire** — stockage contrats/factures/bons, rattachement à une opération, recherche,
    contrôle d'accès par rôle.
14. **Taxes (TVA)** — taux global + par catégorie, application auto, HT/TTC, rapports, multi-taxes.
15. **Multi-entreprise (SaaS)** — espaces isolés par entreprise, super-admin, facturation,
    activation/désactivation sans perte de données.

---

## 2. Fonctionnalités transversales

- **Tableau de bord & analytique** — dashboards par rôle, CA jour/semaine/mois, bénéfices,
  dépenses, stock critique, graphiques (ventes, top produits, rotation), comparaison zones/dépôts,
  export PDF/Excel.
- **Notifications & alertes** — in-app temps réel + email ; rupture, échéance client, maintenance,
  expiration documents, écarts de caisse, litiges, caisse négative ; centre de notifications.
- **Messagerie interne** — communication entre utilisateurs, discussions liées à une opération.
- **Objectifs commerciaux** — objectifs par dépôt/période, suivi temps réel, rapports.
- **API & intégrations** — API REST documentée (Swagger/OpenAPI), intégration mobile money
  (Orange Money API), export comptable.

---

## 3. Cœur vs optionnel

**Cœur de projet** (à livrer) : tout le périmètre fonctionnel et transversal ci-dessus, dont le
mode logistique **Standard QR + GPS** (obligatoire) et la **signature de réception** (obligatoire).

**Optionnel** (implémenté si le temps le permet, sinon documenté comme amélioration future) :

| Option | Note |
|---|---|
| **Traçage NFC des véhicules** | Requiert une puce NFC physique par véhicule ; ajoute une vérification de présence avant démarrage. Le QR reste obligatoire. |
| **Scan code-barres par téléphone** | Via navigateur mobile (API caméra) ; ventes et inventaires. Aucun équipement spécial. |
| **Module IA** | Prévision des ventes, réappro intelligent, détection d'anomalies, analyse de tendances. Nécessite un historique suffisant. |
| **2FA** | Code temporaire (SMS/app) en plus du mot de passe. Le JWT + blocage de compte couvre déjà la base. |
| **Cartographie avancée** | Polygones de zone (Leaflet.draw → GeoJSON), surfaces colorées, marqueurs par dépôt, validation dépôt dans sa zone. En base : un simple marqueur central par zone. |

---

## 4. Exigences non fonctionnelles

- **Performance** : < 2 s pour 95 % des requêtes ; ≥ 50 utilisateurs simultanés.
- **Sécurité** : JWT + refresh token ; chiffrement des données sensibles ; protection CSRF/XSS/SQLi ;
  expiration de session ; sauvegardes quotidiennes ; blocage après tentatives échouées ; journal de connexion.
- **Disponibilité** : cible 99 % ; **mode offline partiel** (saisie sans connexion + synchro ultérieure).
- **Ergonomie** : responsive (desktop prioritaire, tablette/mobile pour chauffeurs) ; interface
  **entièrement en français** ; recherche globale ; retours visuels clairs.

---

## 5. Stack technique

| Composant | Technologie |
|---|---|
| Frontend | Angular (LTS) |
| Backend | Django REST Framework |
| Base de données | PostgreSQL |
| Authentification | JWT (SimpleJWT) |
| Cartographie | OpenStreetMap / Leaflet.js |
| Suivi GPS | API Geolocation navigateur (polling ~1 min) |
| Temps réel / NFC (opt.) | WebSockets ou polling périodique |
| Signatures | Canvas HTML5 |
| Stockage fichiers | AWS S3 ou stockage local (configurable) |
| Déploiement | Docker + Nginx |
| Doc API | Swagger / drf-spectacular |

Architecture : client-serveur découplée (SPA Angular + API REST DRF) ; séparation logique par
entreprise/zone/dépôt ; permissions multi-niveaux côté backend ; isolation des données par
entreprise (SaaS).

---

## 6. Contraintes & hypothèses

- Échéance de déploiement : **29/05/2026**.
- Contexte **guinéen** : GNF, Orange Money, MTN Money.
- **Web-only** dans cette version (pas d'app mobile native) ; GPS et signature via navigateur mobile.
- Connectivité instable → interface résiliente (timeouts gérés, messages clairs).
- Hébergement **on-premise** ou cloud contrôlé par l'entreprise.
- Signature de réception **obligatoire** ; NFC **optionnel par véhicule** ; options reportées en
  amélioration future si le temps manque.
