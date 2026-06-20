"""
apps/ventes/services.py
Logique métier pour la création de commandes et paiements.
"""

from decimal import Decimal

from django.db import transaction

from apps.produits.models import Produit
from apps.stocks.services import sortie_stock

from .models import Client, Commande, HistoriquePoints, LigneCommande, Paiement, ParametresFidelite


def creer_commande(company, depot, caissier, lignes_data,
                   client=None, mode_paiement=Commande.ModePaiement.COMPTANT,
                   remise=Decimal('0'), points_utilises=0, notes='',
                   montant_paye=Decimal('0'),
                   mode_paiement_initial=Paiement.Mode.ESPECES,
                   reference_paiement='', compte_mobile_money=None):
    """
    Crée une commande, ses lignes, débite le stock et enregistre le 1er paiement.
    """
    with transaction.atomic():
        # 1. Résoudre les produits et calculer les totaux
        total_ht = Decimal('0')
        total_tva = Decimal('0')
        lignes_resolved = []

        for ligne in lignes_data:
            produit = Produit.objects.get(pk=ligne['produit'], company=company, is_active=True)
            prix_ht = ligne.get('prix_unitaire_ht', produit.prix_vente)
            qte = Decimal(str(ligne['quantite']))
            tva_taux = produit.tva_taux
            mht = qte * Decimal(str(prix_ht))
            mtva = mht * tva_taux / 100
            total_ht += mht
            total_tva += mtva
            lignes_resolved.append({
                'produit': produit,
                'quantite': qte,
                'prix_unitaire_ht': Decimal(str(prix_ht)),
                'tva_taux': tva_taux,
                'montant_ht': mht,
                'montant_tva': mtva,
                'montant_ttc': mht + mtva,
            })

        total_ttc = total_ht + total_tva

        # 2. Points fidélité → réduction
        reduction_points = Decimal('0')
        if points_utilises > 0 and client:
            try:
                params = company.parametres_fidelite
                if params.is_active and client.points_fidelite >= points_utilises:
                    reduction_points = (
                        Decimal(str(points_utilises)) * params.valeur_point_gnf
                    )
            except ParametresFidelite.DoesNotExist:
                points_utilises = 0

        remise_totale = remise + reduction_points

        # 3. Créer la commande
        commande = Commande.objects.create(
            company=company, depot=depot, client=client,
            mode_paiement=mode_paiement,
            montant_ht=total_ht,
            tva_total=total_tva,
            montant_ttc=total_ttc,
            remise=remise_totale,
            notes=notes,
            caissier=caissier,
            points_utilises=points_utilises,
        )

        # 4. Créer les lignes
        for ligne in lignes_resolved:
            LigneCommande.objects.create(commande=commande, **ligne)

        # 5. Débit stock et calcul points gagnés
        points_gagnes = 0
        for ligne in lignes_resolved:
            sortie_stock(
                depot=depot,
                produit=ligne['produit'],
                quantite=ligne['quantite'],
                utilisateur=caissier,
                reference_doc=commande.numero,
                motif="Vente",
            )

        try:
            params = company.parametres_fidelite
            if params.is_active:
                montant_net = total_ttc - remise_totale
                points_gagnes = params.calculer_points(montant_net)
        except ParametresFidelite.DoesNotExist:
            pass

        commande.points_gagnes = points_gagnes
        commande.save(update_fields=['points_gagnes'])

        # 6. Mettre à jour les points client + historique
        if client and points_utilises > 0:
            HistoriquePoints.objects.create(
                client=client,
                type_mouvement=HistoriquePoints.TypeMouvement.UTILISATION,
                points=-points_utilises,
                commande=commande,
                note="Points utilisés en réduction",
            )
        if client and points_gagnes > 0:
            HistoriquePoints.objects.create(
                client=client,
                type_mouvement=HistoriquePoints.TypeMouvement.GAIN,
                points=points_gagnes,
                commande=commande,
                note="Points gagnés sur achat",
            )
        if client and (points_utilises > 0 or points_gagnes > 0):
            client.points_fidelite = (
                client.points_fidelite - points_utilises + points_gagnes
            )
            client.save(update_fields=['points_fidelite'])

        # 7. Enregistrer le paiement initial si non nul
        if montant_paye > 0:
            enregistrer_paiement(
                commande=commande,
                montant=montant_paye,
                mode=mode_paiement_initial,
                caissier=caissier,
                reference=reference_paiement,
                compte_mobile_money=compte_mobile_money,
            )

        # 8. Passer en CONFIRMÉE
        commande.statut = Commande.Statut.CONFIRMEE
        commande.save(update_fields=['statut'])

        return commande


def enregistrer_paiement(commande, montant, mode, caissier, reference='',
                         compte_mobile_money=None):
    """Ajoute un paiement à une commande et met à jour montant_paye + solde client.

    Pour un paiement Orange Money / MTN Money, crédite le compte mobile money
    sélectionné et trace la transaction opérateur (PAIEMENT_RECU).
    """
    with transaction.atomic():
        paiement = Paiement.objects.create(
            commande=commande,
            montant=montant,
            mode=mode,
            reference=reference,
            caissier=caissier,
            compte_mobile_money=compte_mobile_money,
        )

        # Paiement Mobile Money : créditer le compte + journaliser la transaction.
        if compte_mobile_money is not None and mode in (
            Paiement.Mode.ORANGE_MONEY, Paiement.Mode.MTN_MONEY,
        ):
            from apps.finance.models import TransactionMobileMoney
            TransactionMobileMoney.objects.create(
                compte=compte_mobile_money,
                type_transaction=TransactionMobileMoney.TypeTransaction.PAIEMENT_RECU,
                montant=montant,
                reference_operateur=reference,
                reference_doc=commande.numero,
                description=f"Paiement vente {commande.numero}",
                created_by=caissier,
            )
            compte_mobile_money.solde += montant
            compte_mobile_money.save(update_fields=['solde'])

        commande.montant_paye += montant
        commande.save(update_fields=['montant_paye'])

        # Mise à jour du solde crédit client
        if commande.client:
            client = commande.client
            client.solde_credit = max(
                Decimal('0'),
                commande.reste_a_payer
            )
            client.save(update_fields=['solde_credit'])

        return paiement
