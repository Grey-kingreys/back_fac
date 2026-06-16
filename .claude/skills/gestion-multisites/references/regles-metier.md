# Règles Métier — Référence détaillée

## Table des matières

0. Modèle hiérarchique des entités & rattachements
0bis. La mission logistique : définition, types, cycle de vie
1. Hiérarchie des caisses physiques
2. Comptes de paiement mobile (Orange / MTN Money)
3. Multi-devises
4. Logistique : modes de transport, GPS, signature, litiges
5. Statuts d'une mission
6. Stock : FIFO/FEFO, transferts, inventaires, ajustements
7. Ventes & clients : paiements, devis, retours, TVA
8. Fidélité client
9. TVA
10. Mode multi-entreprise (SaaS)
11. Planification des transferts de stock

---

## 0. Modèle hiérarchique des entités & rattachements

Tout l'édifice repose sur une chaîne d'appartenance stricte. Aucune entité opérationnelle ne
« flotte » sans parent.

```
Plateforme
└── Entreprise (= tenant)
    └── Zone (FK obligatoire → entreprise)
        └── Dépôt (FK obligatoire → zone)
            └── Personnel + Caisse dépôt + Comptes mobiles + Véhicules
```

| Entité | Rattachée à | Géolocalisation | Géré par |
|---|---|---|---|
| **Entreprise** | Plateforme | — | Administrateur (de l'entreprise) |
| **Zone** | Entreprise (obligatoire) | **Point central** (lat/long, clic carte) | **Responsable de zone** (par défaut : un Superviseur affecté à la zone) |
| **Dépôt** | Zone (obligatoire) | **Position propre** (lat/long du dépôt) | **Gestionnaire** (responsable du dépôt) |

Affectation du **personnel** (un agent appartient à un niveau précis) :

| Rôle | Niveau d'affectation |
|---|---|
| Super-administrateur | Plateforme |
| Administrateur | Entreprise |
| Superviseur / Responsable de zone | Zone (une ou plusieurs) |
| Gestionnaire | Dépôt (le sien) |
| Caissier | Dépôt |
| Commercial | Dépôt |
| Chauffeur | Dépôt (dépôt d'attache) |
| Maintenancier | Dépôt ou zone (selon l'organisation de la flotte) |

Conséquences pratiques :
- Un **caissier**, un **commercial**, un **chauffeur** sont **toujours rattachés à un dépôt**.
  Leurs droits et leurs données sont donc bornés à ce dépôt (et, par héritage, à sa zone et son
  entreprise).
- La **caisse dépôt** appartient au dépôt ; la **session caissier** appartient à un caissier de ce
  dépôt ; la **caisse zone** consolide les caisses dépôt de la zone — d'où l'alignement parfait avec
  la hiérarchie financière (§1).
- Un **dépôt a sa propre position GPS** : il s'affiche comme un marqueur *à l'intérieur* du
  périmètre de sa zone (le marqueur de zone reste le point central de la zone).

---

## 0bis. La mission logistique : définition, types, cycle de vie

**Définition** — Une **mission** est une opération de transport physique, exécutée par un
**chauffeur** avec un **véhicule**, reliant un point de départ à un point d'arrivée, avec preuve
de réalisation (QR au départ, GPS pendant, signature/réception à l'arrivée).

**Qui l'initie ?** — C'est le **gestionnaire (responsable du dépôt)** concerné qui **initie** la
mission, pas seulement l'administrateur. (Le responsable de zone / superviseur peut intervenir en
validation, notamment pour l'inter-zone.) Le chauffeur ne crée jamais une mission : il l'exécute.

**Trois types de mission :**

| Type | Origine → Destination | Déclencheur métier | Preuve à l'arrivée |
|---|---|---|---|
| **Transfert** inter-dépôt (ou inter-zone) | Dépôt A → Dépôt B | Demande de transfert validée (manuelle ou recommandée par seuils) | Réception au dépôt destinataire (+ signature) |
| **Livraison client** | Dépôt → Client | Commande client (créée par le commercial) | Signature de réception du client (ePOD) |
| **Enlèvement fournisseur** | Fournisseur → Dépôt | Approvisionnement / commande fournisseur | Bon de réception au dépôt (contrôle des quantités) |

**Cycle de vie commun** (identique pour les 3 types) :
1. Le **gestionnaire** initie la mission (et, si requis, elle est **validée** par le responsable de
   zone / superviseur — surtout en inter-zone).
2. Un **QR code** unique est généré ; un **chauffeur** + **véhicule** sont assignés.
3. Le chauffeur **scanne le QR** (mode NFC optionnel : scan de la puce du véhicule en plus) →
   départ enregistré.
4. **GPS** actif (~1 min) pendant le trajet ; statuts mis à jour (cf. §5).
5. À l'arrivée : **preuve** selon le type (signature client / réception dépôt). Manquants →
   réserve + motif + alerte ; refus → **Litige** + alerte superviseur.
6. Génération du **bon de livraison/réception PDF** ; mission **Terminée**.

> Lien stock ↔ logistique : un transfert validé **déclenche** une mission de type *Transfert* ;
> une commande client peut déclencher une mission de type *Livraison* ; un approvisionnement, une
> mission de type *Enlèvement*. La mission est le bras « transport » de ces opérations.

---

## 1. Hiérarchie des caisses physiques

Quatre niveaux. Chaque niveau **consolide automatiquement** les fonds du niveau inférieur à sa
fermeture :

```
Caisse Entreprise (permanente) → Caisse Zone → Caisse Dépôt → Session Caissier
```

Règles applicables à **toute** caisse (priment sur les rôles) :

| Règle | Détail |
|---|---|
| Jamais supprimée | Une caisse fermée reste en base définitivement |
| Jamais réouverte | Une caisse fermée ne peut plus être modifiée |
| Motif obligatoire | Tout écart à la fermeture exige un motif saisi |
| Double comptage | Le receveur compte lui-même et saisit son propre montant |
| Justificatif | Tout versement inter-niveau nécessite un justificatif joint |
| Blocage | Impossible de fermer une caisse si des sous-caisses sont ouvertes |

La **Caisse Entreprise** est permanente (jamais fermée dans le cours normal). La validation des
**caisses de zone** est une prérogative de l'**administrateur**.

---

## 2. Comptes de paiement mobile (Orange Money / MTN Money)

Même hiérarchie et **mêmes règles** que les caisses physiques (jamais supprimée, jamais réouverte,
écart→motif, etc.). Spécificités :

- Chaque transaction mobile **doit** inclure l'**ID de transaction de l'opérateur**.
- À la fermeture : **capture du relevé de compte opérateur** comme justificatif.
- Le système **compare** le solde virtuel calculé au relevé réel ; tout écart exige un motif.

---

## 3. Multi-devises

- L'administrateur configure les devises disponibles (GNF, USD, EUR, …).
- Les **taux de conversion** ont une **date d'expiration** (ex. 1 USD = 8 600 GNF jusqu'au
  30/04/2026). Le système **alerte à l'expiration** du taux.
- Chaque caisse reçoit une **devise à sa création** (assignée par l'admin).
- Les **rapports consolidés** convertissent automatiquement toutes les caisses dans la **devise
  principale** de l'entreprise. L'admin dispose d'une vue récapitulative de tous les soldes
  convertis.

---

## 4. Logistique : modes de transport, GPS, signature, litiges

Deux modes partageant le **même processus de base** ; seule différence = la validation NFC.

| Mode | Processus | Différence |
|---|---|---|
| **Standard (sans NFC)** — *obligatoire* | Création mission → QR généré → chauffeur scanne le QR → mission démarre (heure enregistrée) → GPS téléphone toutes les ~1 min → signature à l'arrivée | Aucun équipement spécial |
| **Avancé (avec NFC)** — *optionnel* | Idem + scan de la puce NFC fixée sur le véhicule pour vérifier la présence physique avant démarrage | Puce NFC installée |

**Suivi GPS (mode standard)** : à la création, un QR unique est généré ; le chauffeur le scanne
pour démarrer ; le GPS s'active et envoie la position toutes les ~1 min ; le système enregistre
départ, trajet, distance, arrivée.

**Signature numérique de réception** (obligatoire dans tous les cas) :
- Le destinataire vérifie les produits et signe sur l'écran du téléphone du chauffeur.
- La signature est **horodatée** et rattachée définitivement à la mission ; un bon de livraison
  signé est généré en PDF.
- **Produits manquants** → signature **avec réserve** + **motif obligatoire** + **alerte responsable**.
- **Refus de signature** → mission en statut **Litige** + **alerte immédiate au superviseur**.

---

## 5. Statuts d'une mission

| Statut | Description |
|---|---|
| Planifiée | Mission créée, transport pas encore démarré |
| Chargement en cours | Chargement des marchandises en cours |
| Transport en cours | Camion en route vers la destination |
| Arrivé à destination | Camion arrivé, en attente de signature |
| Litige | Refus de signature ou problème signalé à l'arrivée |
| Terminée | Mission clôturée, signature de réception validée |

Alertes auto du tableau de bord logistique : arrêt prolongé, retard, perte de signal GPS,
mission en litige.

---

## 6. Stock : FIFO/FEFO, transferts, inventaires, ajustements

- **FIFO par défaut** (First In, First Out) sur les mouvements de stock.
- **FEFO** (First Expired, First Out) pour les **produits périmables** (suivi des dates d'expiration).
- **Seuils de stock minimum** par produit, avec **alertes automatiques** de rupture.
- **Transferts inter-dépôts** — workflow en 4 temps avec traçabilité complète :
  **demande → validation → expédition → réception**. Une fois validé, un transfert **déclenche la
  création d'une mission logistique**.
- **Inventaires physiques** périodiques avec **détection des écarts**.
- **Ajustements de stock** : correction avec **motif obligatoire** + **validation superviseur**
  (le gestionnaire demande, le superviseur valide).
- **Historique complet** de tous les mouvements (qui, quand, quoi, quelle quantité).

---

## 7. Ventes & clients : paiements, devis, retours, TVA

- **Modes de paiement** : comptant, partiel, à crédit. Suivi des **créances** + relances automatiques.
- **Devis** convertibles en commande ; commande avec sélection du **dépôt source**.
- **Bons de livraison** et **factures PDF** à **numérotation automatique**.
- **Retours clients** et remboursements gérés ; historique complet par client.
- **Remises/promotions** par produit, client ou période.
- **TVA appliquée automatiquement** sur les factures (voir §9).

---

## 8. Fidélité client

- Attribution **automatique** de points à chaque achat, selon un **barème configurable** par l'admin.
- Conversion des points en réductions / bons d'achat (ex. 100 points = réduction).
- Règles (taux, seuils, validité) configurées par l'administrateur.
- Historique des points gagnés/utilisés ; **notification** au client à l'atteinte d'un seuil.

---

## 9. TVA

- Configuration d'un **taux global** et de taux **par catégorie de produit**.
- **Application automatique** sur les factures de vente ; affichage **HT et TTC**.
- **Rapports de TVA collectée** par période ; paramétrage **multi-taxes** pour s'adapter aux
  réglementations locales.

---

## 10. Mode multi-entreprise (SaaS)

- Plusieurs entreprises indépendantes sur une même plateforme, **espaces isolés**.
- **Isolation complète** des données (aucun accès croisé) — règle universelle.
- Chaque entreprise configure ses propres zones, dépôts, produits, utilisateurs, paramètres financiers.
- **Facturation/abonnement par entreprise** (configurable).
- **Super-administrateur** : tableau de bord global, **activation/désactivation** d'une entreprise
  **sans perte de données**.

---

## 11. Planification des transferts de stock

- **Mode automatique** : analyse périodique des niveaux de stock → recommandations de transfert
  **soumises à validation**.
- **Mode manuel** : transfert **initié par le gestionnaire** du dépôt d'origine (l'administrateur
  peut aussi en créer). La **validation** revient au responsable de zone / superviseur, surtout
  pour un transfert **inter-zone**.
- Notifications (in-app + email) aux responsables : produit, quantité, sites, date suggérée.
- Une fois validé, le transfert **déclenche une mission logistique de type *Transfert*** (cf. §0bis)
  — lien direct stock ↔ logistique.
