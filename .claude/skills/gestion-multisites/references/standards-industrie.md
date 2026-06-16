# Standards de l'industrie & Bonnes pratiques

Ce fichier ancre les règles métier du CDC dans les **standards reconnus** (ERP, contrôle
interne, logistique, SaaS). Objectif : donner les **noms formels** des concepts, valider les
choix du projet, et signaler les bonnes pratiques à respecter pour ne pas réinventer la roue.
Chaque section suit le schéma : *ce que dit le CDC → standard correspondant → à retenir*.

## Table des matières

1. RBAC : modèle de permissions à plusieurs niveaux
2. Séparation des tâches & maker-checker (anti-fraude)
3. Manipulation du cash : les 4 étapes & l'immuabilité
4. Stratégies de sortie de stock : FIFO / LIFO / FEFO
5. Preuve de livraison électronique (ePOD)
6. Isolation multi-tenant (SaaS) & Row-Level Security
7. Réconciliation des paiements & mobile money
8. Maintenance de flotte : préventive vs prédictive
9. Sources de référence

---

## 1. RBAC : modèle de permissions à plusieurs niveaux

**CDC** : 8 rôles, « permissions granulaires (lecture seule / écriture / validation) », un
gestionnaire agit sur « son dépôt », un chauffeur sur « ses missions ».

**Standard** : les ERP matures (ERPNext/Frappe, Odoo) ne s'arrêtent pas au rôle. Ils combinent
**quatre niveaux** de contrôle d'accès, à reproduire ici :

1. **Rôle (role)** : autorise des *actions* (lire, écrire, créer, valider, exporter) sur un *type
   d'objet* (produit, commande, caisse…). C'est le niveau de base.
2. **Permission par enregistrement (record-level / user permission)** : restreint un utilisateur
   à *certains enregistrements* d'un type. C'est exactement « son dépôt », « ses missions ». Dans
   ERPNext on lie l'utilisateur à une valeur (un dépôt, un territoire) et la restriction se
   propage à tout objet lié. → Côté DRF, implémenter une **permission d'objet** (`has_object_permission`)
   filtrant par dépôt/zone/entreprise, pas seulement une permission de vue.
3. **Permission par champ (field-level / permission "level")** : certains champs d'un même objet
   sont masqués/non modifiables selon le rôle (ex. un caissier voit le montant mais pas la marge).
4. **Étapes du document (document stages)** : les droits varient selon l'état — créer, enregistrer,
   **soumettre/valider**, annuler, amender. C'est le bon cadre pour « le gestionnaire crée la
   demande d'ajustement, le superviseur la valide ».

**À retenir** : un *partage temporaire* (donner un accès ponctuel à un document précis à un
utilisateur, puis le retirer) est un motif courant et utile — prévoir le cas plutôt que d'élargir
le rôle. Toujours appliquer le **moindre privilège** : on accorde, on n'enlève pas.

---

## 2. Séparation des tâches & maker-checker (anti-fraude)

**CDC** : « ajustement → motif + validation superviseur », « le receveur compte lui-même »,
« justificatif obligatoire », journal d'audit.

**Standard** : c'est la **séparation des tâches** (*Segregation of Duties*, SoD), pilier du
contrôle interne. Principe : **aucune personne** ne doit cumuler, sur une même transaction,
l'**autorisation**, la **garde de l'actif** (custody) et l'**enregistrement** (recordkeeping).
La mise en œuvre par double validation s'appelle **maker-checker** (ou **4-eyes / double
regard**) : un acteur crée, un *autre* confirme. C'est le standard bancaire.

Pour le cash spécifiquement, les manuels de contrôle interne découpent la manipulation en
**quatre étapes idéalement tenues par des personnes différentes** : **recevoir → déposer →
enregistrer → réconcilier**. La personne qui collecte ne doit pas être celle qui réconcilie.

**Mapping CDC → SoD**
- Gestionnaire *demande* l'ajustement / superviseur *valide* → maker-checker. ✅ Bon réflexe.
- Double comptage + justificatif joint → séparation custody/recording + documentation. ✅
- Caissier qui encaisse ≠ celui qui valide la caisse de zone (admin) → séparation autorisation/garde. ✅

**À retenir** : la limite classique de la SoD est le **manque d'effectif** (petite équipe = mêmes
mains). Le palliatif reconnu : **revue/supervision** renforcée + **piste d'audit** complète. C'est
précisément pourquoi le journal d'audit du CDC est non négociable.

---

## 3. Manipulation du cash : les 4 étapes & l'immuabilité

**CDC** : hiérarchie de caisses, « jamais supprimée », « jamais réouverte », écart → motif.

**Standard** : une caisse fermée = un **enregistrement comptable immuable**. Le contrôle interne
exige que les pièces ne soient ni modifiables ni effaçables a posteriori (sinon la piste d'audit
perd toute valeur probante). La consolidation niveau par niveau correspond à un **dépôt/versement**
avec rapprochement à chaque palier.

**À retenir** : techniquement, ne jamais faire de `UPDATE`/`DELETE` destructif sur une caisse
fermée. Modéliser plutôt en **append-only** (les corrections se font par une *nouvelle* écriture
motivée, pas par modification de l'ancienne) — c'est le comportement attendu d'un grand livre.

---

## 4. Stratégies de sortie de stock : FIFO / LIFO / FEFO

**CDC** : FIFO par défaut, FEFO pour les périmables.

**Standard** (documentation Odoo) : ce sont des **removal strategies** appliquées au niveau de la
catégorie de produit ou de l'emplacement.
- **FIFO** (First In, First Out) : sort en premier ce qui est entré en premier. Adapté à la
  plupart des cas, y compris produits à rotation.
- **LIFO** (Last In, First Out) : sort le plus récent. **Interdit dans de nombreux pays** car il
  peut laisser vieillir/périmer le stock ancien → à éviter ici.
- **FEFO** (First Expired, First Out) : sort en premier ce qui **expire** le plus tôt (≠ date
  d'entrée). Pour médicaments, alimentaire, cosmétiques. Notion clé : une **date de retrait**
  (combien de jours *avant* péremption le produit doit sortir du stock). Les lots sans date de
  retrait passent *après* ceux qui en ont une.

**À retenir** : FEFO suppose de tracer un **lot** + sa **date d'expiration** par entrée ; sans
gestion de lots, FEFO n'a pas de sens. Le choix FIFO/FEFO se configure par catégorie de produit.

---

## 5. Preuve de livraison électronique (ePOD)

**CDC** : signature numérique horodatée à la réception, bon de livraison PDF, réserve si manquants,
statut Litige si refus, photo (optionnelle).

**Standard** : c'est l'**ePOD** (*electronic Proof of Delivery*). Les composants reconnus d'un bon
ePOD : **signature**, **horodatage**, **géolocalisation (geotag)**, **photo**, et la possibilité de
rendre certains champs **obligatoires** (signature/photo/quantité). Bénéfices documentés : preuve de
condition des marchandises, **réduction des litiges et des réclamations frauduleuses** (manquants,
vol, dommages), facturation plus rapide, visibilité temps réel pour le dispatcher.

**À retenir** : le CDC est déjà aligné. Deux ajouts gratuits et standards : **géotaguer** la
signature (lat/long au moment de signer, pas seulement l'heure) et autoriser une **photo de
preuve** à la livraison — c'est le couple signature+photo qui coupe court aux litiges. La
**vérification du contenu** peut s'appuyer sur le scan code-barres (cf. option du CDC).

---

## 6. Isolation multi-tenant (SaaS) & Row-Level Security

**CDC** : mode multi-entreprise, « isolation complète des données, aucun accès croisé ».

**Standard** : trois modèles d'isolation, du plus fort au plus mutualisé :
- **Base par tenant** (database-per-tenant) : isolation maximale, coûteux à exploiter à grande échelle.
- **Schéma par tenant** (schema-per-tenant) : isolation moyenne, bon compromis pour des clients exigeants.
- **Schéma partagé + `tenant_id`** (shared / pool) : le plus économique, mais **le plus risqué** :
  *un seul `WHERE entreprise_id = ?` oublié dans une requête = fuite de données entre entreprises*.

**Pertinent pour la stack Django/PostgreSQL** : au-delà du filtre applicatif, PostgreSQL offre la
**Row-Level Security (RLS)** — le moteur lui-même filtre les lignes selon le contexte (l'entreprise
courante), via des *policies*. C'est un **filet de sécurité (défense en profondeur)** qui rattrape
les oublis du code applicatif. Recommandation standard : `tenant_id` (ici `entreprise_id`) sur
**chaque** table multi-tenant + index dessus + policies RLS, et tester les cas limites (pooling de
connexions, opérations en masse, accès admin).

**À retenir** : ne jamais faire reposer l'isolation SaaS sur la seule discipline des développeurs à
écrire le bon `WHERE`. Combiner filtrage applicatif **et** RLS.

---

## 7. Réconciliation des paiements & mobile money

**CDC** : chaque transaction mobile porte l'**ID opérateur** ; à la fermeture, capture du relevé
et **comparaison solde calculé vs relevé réel** ; écart → motif.

**Standard** : c'est de la **réconciliation de paiements**. Le processus type : (1) collecter les
données des deux côtés (système interne + relevé opérateur), (2) **normaliser** (formats, horodatage,
devise, références), (3) **matcher** transaction par transaction via l'**ID de transaction** — c'est
*le pont* entre l'enregistrement interne et le relevé externe, (4) **identifier les exceptions**
(non rapprochées, partielles, montants divergents), (5) **résoudre** avec motif et **piste d'audit**.

**Mapping CDC → réconciliation** : l'ID de transaction obligatoire = la **clé de rapprochement** ;
le relevé opérateur = la **source externe de vérité** ; l'écart motivé = la **gestion d'exception**.
✅ Le CDC applique le bon schéma.

**À retenir** : prévoir aussi le rapprochement des **frais opérateur** (commission Orange/MTN) qui
expliquent une partie des écarts attendus ; les modéliser comme une catégorie de dépense plutôt
que comme un « écart inexpliqué ».

---

## 8. Maintenance de flotte : préventive vs prédictive

**CDC** : maintenance préventive et corrective ; « prédictive : alertes basées sur le kilométrage
ou les échéances calendaires ».

**Standard** : vocabulaire de gestion de flotte établi.
- **Corrective** : on répare après la panne.
- **Préventive** : entretien planifié à intervalle fixe (km ou temps) pour *éviter* la panne.
- **Prédictive** : on déclenche l'intervention sur la base d'indicateurs/seuils (km, échéances,
  télémétrie) — c'est exactement la définition du CDC.

**À retenir** : le CDC emploie correctement les termes. La prédictive « km/calendaire » est une
forme simple et réaliste (pas besoin de capteurs IoT). Coupler avec les **rappels d'expiration**
des documents véhicule (assurance, visite technique) déjà prévus.

---

## 9. Sources de référence

À consulter pour approfondir un point précis (noms de sources, à retrouver via recherche) :

- **Stratégies de sortie de stock** : documentation Odoo, « Removal strategies (FIFO, LIFO, FEFO) ».
- **RBAC multi-niveaux** : documentation ERPNext / Frappe, « Role Based Permissions » et
  « User Permissions » (record-level + permission levels + document stages).
- **Séparation des tâches / maker-checker** : guides de contrôle interne (AccountingTools,
  bureaux d'audit universitaires) ; article « Maker-checker (4-eyes) » pour le principe bancaire.
- **ePOD** : documentation des éditeurs de fleet management (Webfleet, Descartes, Detrack) sur la
  composition d'une preuve de livraison (signature, horodatage, geotag, photo, champs obligatoires).
- **Isolation multi-tenant & RLS** : blog AWS « Multi-tenant data isolation with PostgreSQL
  Row-Level Security » ; articles sur les modèles db/schema/shared.
- **Réconciliation de paiements** : guides Stripe / fournisseurs de réconciliation (étapes
  collecte → normalisation → matching par ID → exceptions → audit).
