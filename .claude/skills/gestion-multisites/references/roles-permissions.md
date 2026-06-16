# Rôles & Permissions — Référence détaillée

## Comment lire ce fichier

- Le CDC définit le **périmètre par défaut** de chaque rôle. Les permissions sont
  **granulaires** : un rôle peut être affiné en lecture seule / écriture / validation. Ce qui
  suit décrit donc le *défaut raisonnable*, configurable par l'administrateur.
- **[Explicite]** = écrit noir sur blanc dans le CDC. **[Déduit]** = inféré par périmètre et
  principe de moindre privilège ; à présenter comme tel, pas comme une certitude.
- Les **règles universelles** (immuabilité des caisses, signature obligatoire, isolation SaaS,
  traçabilité…) s'appliquent à *tous* les rôles et priment toujours. Voir `regles-metier.md`.
- **Affectation** : chaque rôle est rattaché à un niveau de la hiérarchie (plateforme / entreprise
  / zone / dépôt). Ses droits et ses données sont bornés à ce périmètre. Voir le §0 de
  `regles-metier.md`. En bref : caissier, commercial, chauffeur et gestionnaire appartiennent à un
  **dépôt** ; superviseur/responsable de zone à une **zone** ; admin à l'**entreprise**.

## Table des matières

1. Super-administrateur (SaaS)
2. Administrateur
3. Superviseur
4. Gestionnaire de stock
5. Caissier
6. Commercial
7. Chauffeur
8. Maintenancier
9. Matrice récapitulative
10. Cas limites & arbitrages fréquents

---

## 1. Super-administrateur (mode SaaS)

**Périmètre** : la plateforme entière, au-dessus des entreprises. C'est le seul rôle qui voit
*plusieurs* entreprises.

**PEUT**
- Créer et gérer plusieurs entreprises sur la plateforme. [Explicite]
- Activer / désactiver une entreprise **sans perte de données**. [Explicite]
- Gérer la facturation et l'abonnement par entreprise. [Explicite]
- Consulter le tableau de bord global (toutes les entreprises actives). [Explicite]

**NE PEUT PAS**
- Gérer le quotidien opérationnel *à l'intérieur* d'une entreprise (zones, dépôts, ventes,
  caisses) — cela relève de l'administrateur de chaque entreprise. [Déduit]
- Briser l'isolation des données entre entreprises pour un usage métier ordinaire ; son rôle
  est l'administration de la plateforme, pas l'exploitation des données client. [Déduit]

---

## 2. Administrateur (d'une entreprise)

**Périmètre** : accès complet *à l'intérieur de son entreprise*. C'est le rôle le plus puissant
au niveau métier.

**PEUT**
- Configurer le système et gérer les utilisateurs de son entreprise. [Explicite]
- **Valider les caisses de zone**. [Explicite] — c'est une prérogative nommément admin.
- Créer/gérer les zones géographiques et placer leur point central sur la carte (lat/long
  enregistrées automatiquement). [Explicite]
- Configurer les devises disponibles, les taux de conversion et leur date d'expiration ;
  assigner une devise à chaque caisse à sa création. [Explicite]
- Configurer le taux de TVA (global et par catégorie). [Explicite]
- Configurer les règles de fidélité (taux, seuils, validité). [Explicite]
- Affecter gestionnaires aux dépôts ; transférer la responsabilité entre gestionnaires
  (avec historique). [Explicite]
- Lancer/valider les transferts de stock en mode manuel. [Explicite]

**NE PEUT PAS**
- Rouvrir, modifier ou supprimer une caisse fermée — règle universelle, sans exception. [Explicite]
- Accéder aux données d'une autre entreprise (isolation SaaS). [Explicite]
- Falsifier un écart sans motif, ni un versement sans justificatif. [Explicite]

---

## 3. Superviseur (et Responsable de zone)

**Périmètre** : supervision **multi-sites** et validation d'opérations sensibles. Rôle plutôt
de contrôle/validation que de saisie. **Affectation** : à une **zone** (un superviseur affecté à
une zone en est le **responsable de zone** par défaut) ou à plusieurs zones / toute l'entreprise.

**PEUT**
- Voir l'ensemble des sites de son périmètre (vue multi-sites) et les rapports consolidés. [Explicite]
- Être le **responsable de zone** : superviser les dépôts de sa zone, **valider** les transferts
  (surtout inter-zone) et les missions inter-zone. [Déduit, voir regles-metier §0bis/§11]
- Valider les **opérations sensibles**. [Explicite] — typiquement les **ajustements de stock**
  (le CDC exige une « validation superviseur » sur les ajustements). [Explicite]
- Recevoir et traiter les alertes (écarts de caisse, missions en litige, caisse négative,
  anomalies financières). [Déduit]

**NE PEUT PAS**
- Se substituer à l'administrateur pour la **configuration système** ou la **validation des
  caisses de zone** (prérogative admin). [Déduit]
- Encaisser à la place d'un caissier ni rouvrir une caisse fermée. [Déduit + universel]

> Note 1 : le partage exact « valide quoi » entre Superviseur et Administrateur est configurable.
> Par défaut : Admin = configuration + caisses de zone ; Superviseur = opérations courantes
> sensibles (ajustements, validations de transferts, traitement des litiges).
> Note 2 : « **Responsable de zone** » n'est pas un rôle distinct dans le CDC d'origine — c'est, par
> défaut, un **Superviseur affecté à une zone**. Si l'implémentation préfère un rôle dédié, le
> garder cohérent avec ce périmètre (gestion + validation au niveau zone).

---

## 4. Gestionnaire de stock (responsable du dépôt)

**Périmètre** : produits, mouvements, approvisionnements et transferts **de SON dépôt**. C'est le
**responsable du dépôt** : il gère le dépôt et **initie les missions** qui en partent. **Affectation** :
un dépôt (le sien).

**PEUT**
- Créer/gérer les fiches produits (référence, catégorie, unité, variantes, seuils mini). [Explicite]
- Enregistrer les approvisionnements fournisseurs avec bons de réception. [Explicite]
- Initier une **demande** de transfert inter-dépôt, expédier, réceptionner (avec traçabilité). [Explicite]
- **Initier les missions logistiques** qui partent de son dépôt — les trois types : **transfert**
  inter-dépôt/zone, **livraison** client, **enlèvement** fournisseur (cf. regles-metier §0bis).
  [Déduit du modèle révisé]
- Saisir les **inventaires physiques** et faire remonter les écarts détectés. [Explicite]
- **Demander** un ajustement de stock avec motif obligatoire. [Explicite]

**NE PEUT PAS**
- **Valider** lui-même son propre ajustement de stock — cette validation revient au superviseur
  (séparation des tâches anti-fraude). [Explicite : « validation superviseur »]
- **Valider** seul un transfert **inter-zone** — validation responsable de zone / superviseur. [Déduit]
- Agir sur un **autre** dépôt que le sien. [Explicite : « son dépôt »]
- Gérer les caisses, ni encaisser, ni configurer le système. [Déduit]
- **Conduire/exécuter** la mission lui-même : il l'initie, le **chauffeur** l'exécute. [Déduit]

---

## 5. Caissier

**Périmètre** : **SA** session de caisse uniquement (le niveau le plus bas de la hiérarchie des
caisses). **Affectation** : un **dépôt** (sa session s'ouvre sous la caisse de ce dépôt).

**PEUT**
- Ouvrir et fermer **sa** session de caisse. [Explicite]
- Enregistrer les ventes et les paiements (comptant, partiel, à crédit). [Explicite]
- Saisir les transactions mobile money en y joignant l'**ID de transaction opérateur**. [Explicite]
- À la fermeture : pratiquer le **double comptage** (compter et saisir son propre montant),
  motiver tout écart. [Explicite]

**NE PEUT PAS**
- Rouvrir/modifier une session fermée. [Explicite, universel]
- Valider/fermer une caisse de niveau supérieur (dépôt, zone, entreprise). [Déduit]
- Configurer devises, taux, TVA ou règles de fidélité (admin). [Déduit]
- Modifier le stock physique (rôle gestionnaire). [Déduit]

---

## 6. Commercial

**Périmètre** : relation client en amont de la vente — **clients, devis, commandes**.
**Affectation** : un **dépôt** (il vend depuis le stock de son dépôt ; le « dépôt source » d'une
commande est par défaut le sien).

**PEUT**
- Créer/gérer les fiches clients (particuliers et entreprises). [Explicite]
- Établir des **devis** et les convertir en **commandes**. [Explicite]
- Enregistrer les commandes en sélectionnant le **dépôt source**. [Explicite]
- Appliquer remises et promotions (par produit, client, période) dans le cadre prévu. [Explicite]
- Suivre les créances clients et déclencher des relances. [Déduit]

**NE PEUT PAS**
- **Valider une caisse de zone** (prérogative administrateur). [Explicite → réponse type : non]
- Encaisser physiquement / clôturer une session de caisse (c'est le caissier). [Déduit]
- Modifier les niveaux de stock ou valider des ajustements (gestionnaire / superviseur). [Déduit]
- Configurer la TVA, les devises ou les règles de fidélité (admin). [Déduit]
- Gérer la flotte ou les missions logistiques. [Déduit]

---

## 7. Chauffeur

**Périmètre** : **SES** missions de transport. Rôle terrain, principalement sur navigateur mobile.
**Affectation** : un **dépôt d'attache**. Il **exécute** les missions — il ne les crée pas.

**PEUT**
- Consulter **ses** missions. [Explicite]
- Scanner le **QR code** de la mission pour la démarrer (heure de départ enregistrée). [Explicite]
- Activer le **GPS** du téléphone (position envoyée toutes les ~1 min). [Explicite]
- Faire **signer** la réception au destinataire sur son écran (signature horodatée). [Explicite]
- Déclarer une **panne** véhicule. [Explicite]
- Le cas échéant (mode avancé optionnel) : scanner la **puce NFC** du véhicule avant démarrage. [Explicite, optionnel]

**NE PEUT PAS**
- **Créer/initier** une mission — c'est le **gestionnaire (responsable du dépôt)** qui l'initie ;
  le chauffeur ne fait que l'exécuter. [Déduit du modèle révisé]
- Clôturer une mission sans signature de réception. [Explicite, universel]
- Accéder aux modules financiers, stock ou clients. [Déduit]
- Voir les missions des autres chauffeurs (portée « ses missions »). [Déduit]

> En cas de produits manquants : signature **avec réserve** + motif obligatoire + alerte
> responsable. En cas de refus de signer : mission en statut **Litige** + alerte immédiate au
> superviseur. (Voir `regles-metier.md`.)

---

## 8. Maintenancier

**Périmètre** : maintenance des véhicules et interventions.

**PEUT**
- Enregistrer les interventions de maintenance **préventive** et **corrective**. [Explicite]
- Suivre les pannes : prise en charge, suivi de réparation, coût associé. [Explicite]
- Renseigner les documents véhicule (assurance, visite technique) et leurs échéances. [Déduit]
- Consulter l'historique des interventions par véhicule. [Explicite]

**NE PEUT PAS**
- Conduire / démarrer des missions de transport (rôle chauffeur). [Déduit]
- Gérer le stock, les ventes, les caisses ou les clients. [Déduit]
- Planifier les missions ou affecter les chauffeurs (admin / responsable logistique). [Déduit]

---

## 9. Matrice récapitulative

Lecture : ✅ par défaut · ⛔ hors périmètre par défaut · 🔶 validation/supervision ·
— non concerné. (Toujours configurable + soumis aux règles universelles.)

| Capacité | Super-admin | Admin | Superviseur | Gest. stock | Caissier | Commercial | Chauffeur | Maintenancier |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Gérer plusieurs entreprises | ✅ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |
| Configurer le système (devises, TVA, fidélité) | ⛔ | ✅ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |
| Gérer les utilisateurs | ⛔ | ✅ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |
| Valider une **caisse de zone** | ⛔ | ✅ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |
| Valider un **ajustement de stock** | ⛔ | ✅ | 🔶 | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |
| Créer/gérer fiches produits & stock | ⛔ | ✅ | 🔶 | ✅ (son dépôt) | ⛔ | ⛔ | ⛔ | ⛔ |
| Demander un transfert inter-dépôt | ⛔ | ✅ | 🔶 | ✅ | ⛔ | ⛔ | ⛔ | ⛔ |
| Ouvrir/fermer **sa** session de caisse | ⛔ | ✅ | ⛔ | ⛔ | ✅ | ⛔ | ⛔ | ⛔ |
| Enregistrer ventes & paiements | ⛔ | ✅ | ⛔ | ⛔ | ✅ | 🔶 (via commande) | ⛔ | ⛔ |
| Gérer clients, devis, commandes | ⛔ | ✅ | ⛔ | ⛔ | ⛔ | ✅ | ⛔ | ⛔ |
| **Initier** une mission (transfert/livraison/enlèvement) | ⛔ | ✅ | 🔶 | ✅ (son dépôt) | ⛔ | ⛔ | ⛔ | ⛔ |
| **Exécuter** une mission (scan QR, GPS) | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ✅ | ⛔ |
| Recueillir la signature de réception | ⛔ | — | — | — | — | — | ✅ | ⛔ |
| Déclarer une panne | ⛔ | ✅ | — | — | — | — | ✅ | ✅ |
| Maintenance véhicule / interventions | ⛔ | ✅ | — | — | — | — | ⛔ | ✅ |
| Rouvrir/supprimer une caisse fermée | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |
| Voir données d'une autre entreprise | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |

---

## 10. Cas limites & arbitrages fréquents

- **« Le commercial peut-il valider une caisse de zone ? »** → **Non.** La validation des caisses
  de zone est une prérogative explicite de l'administrateur. Le commercial gère clients/devis/commandes.
- **« Le gestionnaire de stock peut-il valider son propre ajustement ? »** → **Non.** Il le
  *demande* avec motif ; la **validation revient au superviseur** (séparation des tâches).
- **« Le caissier peut-il fermer la caisse du dépôt ? »** → **Non** par défaut. Le caissier ferme
  *sa* session ; la fermeture du dépôt consolide les sessions et relève du niveau supérieur. Et de
  toute façon, impossible de fermer un niveau tant qu'une sous-caisse est ouverte.
- **« Qui gère un dépôt ? »** → Le **gestionnaire** du dépôt (son responsable). **« Qui gère une
  zone ? »** → Un **responsable de zone**, par défaut un **Superviseur affecté à cette zone**.
- **« Qui crée/initie une mission ? »** → Le **gestionnaire (responsable du dépôt)** d'origine.
  Le chauffeur l'**exécute** (scan QR, GPS, signature). L'inter-zone est en général **validé** par
  le responsable de zone / superviseur.
- **« Un caissier/commercial/chauffeur appartient-il à un dépôt ? »** → **Oui.** Ces rôles sont
  affectés à un **dépôt** ; leurs données sont bornées à ce dépôt (et sa zone/entreprise).
- **« Le chauffeur peut-il clôturer une mission sans signature ? »** → **Non.** La signature de
  réception est obligatoire dans tous les cas ; sinon réserve+motif (manquants) ou statut Litige (refus).
- **« Qui peut rouvrir une caisse fermée ? »** → **Personne**, admin compris. Règle d'immuabilité.
- **« Le maintenancier peut-il démarrer une mission ? »** → **Non**, c'est le chauffeur. Le
  maintenancier intervient sur l'entretien et les pannes, pas sur le transport.
- **« Une entreprise voit-elle les données d'une autre ? »** → **Jamais.** Isolation SaaS totale ;
  seul le super-administrateur a une vue *d'administration* (pas d'exploitation) au-dessus.
- **Conflit rôle vs règle universelle** → la **règle universelle gagne** toujours (immuabilité,
  signature, motif, justificatif, isolation, traçabilité).
