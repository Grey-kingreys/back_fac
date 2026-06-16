---
name: gestion-multisites
description: >-
  Expertise métier de l'application de Gestion Intégrée Multi-Sites (commerciale, financière,
  logistique, RH) pour entreprise multi-sites en contexte guinéen (Angular + Django REST + PostgreSQL).
  À consulter SYSTÉMATIQUEMENT dès qu'une question porte sur QUI a le droit de faire QUOI (rôles,
  permissions, RBAC), sur les règles métier (hiérarchie des caisses, comptes mobile money, multi-devises,
  workflow logistique QR/GPS/NFC, transferts de stock, fidélité, TVA, mode SaaS multi-entreprise), ou
  quand on implémente/décrit un module de cette appli. Déclenche même sans le mot « rôle » : toute
  question du type « est-ce que le commercial peut… », « le maintenancier doit-il… », « qui valide… »,
  « que se passe-t-il à la fermeture d'une caisse », « peut-on rouvrir/supprimer une caisse » doit
  passer par ce skill avant de répondre.
---

# Gestion Intégrée Multi-Sites — Expertise Métier

Référentiel de domaine pour piloter et raisonner sur l'application de gestion intégrée
multi-sites (Groupe 1). Le but : permettre à une IA de répondre **avec exactitude** aux
questions de périmètre des rôles et de règles métier, et de guider l'implémentation des
modules dans le bon sens.

## Vue d'ensemble du domaine

L'application centralise les opérations d'une entreprise disposant de **plusieurs zones
géographiques** et **dépôts**, en contexte guinéen (Franc Guinéen, Orange Money, MTN Money,
connectivité instable). Elle couvre quatre grands domaines :

- **Commercial** : produits, stocks, fournisseurs, ventes, clients, devis, fidélité, TVA.
- **Financier** : hiérarchie de caisses physiques + comptes mobile money, multi-devises, dépenses, rapports.
- **Logistique** : flotte de véhicules, missions de transport (QR + GPS, NFC optionnel), signature de réception, maintenance.
- **Humain & transversal** : RH, utilisateurs/rôles, documentaire, tableaux de bord, notifications, mode SaaS.

### Hiérarchie de rattachement (fondamentale — tout est lié de haut en bas)

```
Plateforme
└── Entreprise            (= le tenant ; appartient à la plateforme)
    └── Zone              (FK obligatoire → entreprise ; point GPS central ; responsable de zone)
        └── Dépôt         (FK obligatoire → zone ; SA propre géolocalisation ; gestionnaire + caisse + comptes mobiles)
            └── Personnel affecté : gestionnaire, caissier, commercial, chauffeur (et maintenancier)
```

Règles de rattachement à ne jamais violer :
- **Tout dépôt appartient à exactement une zone** ; toute zone à exactement une entreprise.
- **Le dépôt a sa propre position géographique** (lat/long), distincte du point central de sa zone.
- **Le personnel opérationnel est affecté à un dépôt** (gestionnaire, caissier, commercial,
  chauffeur). Le superviseur/responsable de zone est rattaché à une **zone** ; l'administrateur à
  l'**entreprise** ; le super-administrateur à la **plateforme**.
- **Qui gère quoi** : un **dépôt** est géré par son **gestionnaire** ; une **zone** par un
  **responsable de zone** (par défaut, un Superviseur affecté à cette zone).

Cette même hiérarchie gouverne la consolidation financière (Caisse Entreprise → Zone → Dépôt →
Session Caissier). Détail des entités et des missions dans `references/regles-metier.md`.

## Comment utiliser ce skill

Selon la question, lire le fichier de référence approprié — ne pas répondre de mémoire sur ces sujets :

| Type de question | Fichier à lire |
|---|---|
| « X peut-il faire Y ? », « qui valide… », périmètre/permissions d'un rôle | `references/roles-permissions.md` |
| Caisses, fermeture/consolidation, mobile money, devises, logistique, statuts de mission, stock (FIFO/FEFO), transferts, fidélité, TVA, isolation SaaS | `references/regles-metier.md` |
| Contenu d'un module, périmètre fonctionnel, cœur vs optionnel, stack technique, exigences non fonctionnelles | `references/modules-perimetre.md` |
| « Comment font les vrais ERP / quel est le nom standard de cette règle / quelle bonne pratique » — séparation des tâches, maker-checker, FEFO, ePOD, Row-Level Security, réconciliation… | `references/standards-industrie.md` |

Pour une question de permission, **toujours** croiser deux choses : (1) le périmètre par défaut
du rôle (`roles-permissions.md`) et (2) les règles universelles ci-dessous, qui s'imposent à
*tous* les rôles sans exception.

## Les rôles en un coup d'œil

Huit rôles (sept opérationnels + le super-administrateur du mode SaaS). Périmètre par défaut :

| Rôle | Domaine | Portée |
|---|---|---|
| **Super-administrateur** | Plateforme SaaS | Toutes les entreprises (création, activation, facturation) |
| **Administrateur** | Configuration + tout métier | Toute SON entreprise |
| **Superviseur** | Supervision + validation | Multi-sites (vue globale, validations sensibles) |
| **Gestionnaire de stock** | Produits, stocks, appro, transferts | SON dépôt |
| **Caissier** | Encaissement | SA session de caisse |
| **Commercial** | Clients, devis, commandes | Commercial |
| **Chauffeur** | Missions de transport | SES missions |
| **Maintenancier** | Maintenance véhicules | Flotte / interventions |

Détail PEUT / NE PEUT PAS pour chaque rôle dans `references/roles-permissions.md`.

## Règles universelles inviolables

Ces règles priment sur le rôle. **Personne** ne peut les contourner, pas même l'administrateur,
car elles protègent la traçabilité et l'anti-fraude — l'objectif central du projet.

1. **Immuabilité des caisses fermées** — une caisse (physique ou mobile) fermée n'est *jamais*
   supprimée de la base et *jamais* réouverte ni modifiée. Aucun rôle n'y déroge.
2. **Motif obligatoire sur tout écart** — tout écart constaté à la fermeture d'une caisse, tout
   ajustement de stock, toute réception avec réserve exige un motif saisi.
3. **Justificatif sur tout versement inter-niveau** — un versement d'une caisse vers le niveau
   supérieur nécessite un justificatif joint ; côté mobile money, le relevé opérateur fait foi.
4. **Double comptage** — à la remise de fonds, le receveur compte lui-même et saisit son propre
   montant (le système ne fait pas confiance à un seul comptage).
5. **Blocage de fermeture si sous-caisses ouvertes** — impossible de fermer une caisse tant
   qu'une caisse de niveau inférieur est encore ouverte.
6. **ID de transaction obligatoire (mobile money)** — chaque opération Orange/MTN Money doit
   porter l'ID de transaction de l'opérateur.
7. **Signature de réception obligatoire** — aucune mission logistique ne se clôture sans
   signature numérique du destinataire (avec réserve + motif si produits manquants ; statut
   *Litige* si refus).
8. **Isolation totale des entreprises (SaaS)** — aucun accès croisé entre entreprises. Un
   utilisateur d'une entreprise ne voit jamais les données d'une autre.
9. **Traçabilité intégrale** — chaque mouvement (qui, quand, quoi, combien) et chaque action
   utilisateur est journalisé (journal d'audit). Aucune opération sensible n'est anonyme.

## Cœur vs optionnel

Sont **optionnelles** (implémentées si le temps le permet, sinon documentées comme améliorations
futures) : le traçage **NFC** des véhicules, le **scan code-barres** par téléphone, le module
**IA** (prévisions/anomalies), la **2FA**, et la **cartographie avancée** (polygones de zone,
marqueurs par dépôt). Tout le reste est cœur de projet. En particulier : le mode logistique
**Standard (QR + GPS)** est **obligatoire**, le mode NFC ne fait que l'enrichir. Détail dans
`references/modules-perimetre.md`.

## Posture quand le CDC est muet

Le CDC fixe les **responsabilités** des rôles, pas une liste exhaustive d'interdictions, et
précise que les permissions sont **granulaires et configurables** (lecture seule / écriture /
validation). Donc :

- Quand une permission est **explicite** dans le CDC, l'affirmer.
- Quand elle est **déduite** (par périmètre + moindre privilège), le dire clairement et la
  présenter comme le *défaut raisonnable*, pas comme une certitude absolue.
- Ne jamais inventer une règle qui contredirait les règles universelles ci-dessus.

Pour justifier ou approfondir une règle, `references/standards-industrie.md` relie chaque choix du
CDC à son standard reconnu (séparation des tâches, maker-checker, FIFO/FEFO, ePOD, Row-Level
Security, réconciliation de paiements) et signale les bonnes pratiques à respecter.
