"""
apps/stocks/services.py
Logique métier pour les mouvements de stock.
"""

from django.db import transaction

from .models import LigneTransfert, LotStock, MouvementStock, StockDepot, TransfertStock


def _get_or_create_stock(depot, produit):
    stock, _ = StockDepot.objects.get_or_create(depot=depot, produit=produit)
    return stock


def entree_stock(depot, produit, quantite, utilisateur,
                 reference_doc='', motif='',
                 numero_lot='', date_expiration=None):
    """Enregistre une entrée de stock et met à jour StockDepot."""
    with transaction.atomic():
        stock = _get_or_create_stock(depot, produit)
        avant = stock.quantite
        stock.quantite += quantite
        stock.save(update_fields=['quantite'])

        mvt = MouvementStock.objects.create(
            depot=depot,
            produit=produit,
            type_mouvement=MouvementStock.TypeMouvement.ENTREE,
            quantite=quantite,
            quantite_avant=avant,
            quantite_apres=stock.quantite,
            reference_doc=reference_doc,
            motif=motif,
            utilisateur=utilisateur,
        )

        if produit.est_perimable and numero_lot:
            LotStock.objects.create(
                stock_depot=stock,
                numero_lot=numero_lot,
                quantite=quantite,
                date_expiration=date_expiration,
            )

        return mvt


def sortie_stock(depot, produit, quantite, utilisateur,
                 reference_doc='', motif=''):
    """Enregistre une sortie de stock. Lève ValueError si stock insuffisant."""
    with transaction.atomic():
        stock = _get_or_create_stock(depot, produit)
        if stock.quantite < quantite:
            raise ValueError(
                f"Stock insuffisant : {stock.quantite} disponible, "
                f"{quantite} demandé(e)."
            )
        avant = stock.quantite
        stock.quantite -= quantite
        stock.save(update_fields=['quantite'])

        return MouvementStock.objects.create(
            depot=depot,
            produit=produit,
            type_mouvement=MouvementStock.TypeMouvement.SORTIE,
            quantite=quantite,
            quantite_avant=avant,
            quantite_apres=stock.quantite,
            reference_doc=reference_doc,
            motif=motif,
            utilisateur=utilisateur,
        )


def creer_transfert(company, depot_source, depot_destination,
                    lignes_data, utilisateur, notes=''):
    """
    Crée un TransfertStock en statut BROUILLON avec ses lignes.
    lignes_data = [{'produit': <Produit>, 'quantite_envoyee': x, 'notes': ''}]
    """
    with transaction.atomic():
        transfert = TransfertStock.objects.create(
            company=company,
            depot_source=depot_source,
            depot_destination=depot_destination,
            notes=notes,
            utilisateur_envoi=utilisateur,
        )
        for ligne in lignes_data:
            LigneTransfert.objects.create(
                transfert=transfert,
                produit=ligne['produit'],
                quantite_envoyee=ligne['quantite_envoyee'],
                notes=ligne.get('notes', ''),
            )
        return transfert


def expedier_transfert(transfert, utilisateur):
    """Passe le transfert en EN_TRANSIT et débite le dépôt source."""
    if transfert.statut != TransfertStock.Statut.BROUILLON:
        raise ValueError("Seul un transfert en brouillon peut être expédié.")

    with transaction.atomic():
        from django.utils import timezone
        for ligne in transfert.lignes.select_related('produit').all():
            sortie_stock(
                depot=transfert.depot_source,
                produit=ligne.produit,
                quantite=ligne.quantite_envoyee,
                utilisateur=utilisateur,
                reference_doc=transfert.numero,
                motif=f"Transfert vers {transfert.depot_destination.code}",
            )
            # Lier le mouvement au transfert
            MouvementStock.objects.filter(
                depot=transfert.depot_source,
                produit=ligne.produit,
                type_mouvement=MouvementStock.TypeMouvement.SORTIE,
                reference_doc=transfert.numero,
            ).update(
                type_mouvement=MouvementStock.TypeMouvement.TRANSFERT_DEPART,
                transfert=transfert,
            )

        transfert.statut = TransfertStock.Statut.EN_TRANSIT
        transfert.date_envoi = timezone.now()
        transfert.save(update_fields=['statut', 'date_envoi'])
        return transfert


def receptionner_transfert(transfert, lignes_recues, utilisateur):
    """
    Réceptionne un transfert : crédite le dépôt destination.
    lignes_recues = [{'ligne_id': x, 'quantite_recue': y}]
    """
    if transfert.statut != TransfertStock.Statut.EN_TRANSIT:
        raise ValueError("Seul un transfert en transit peut être réceptionné.")

    with transaction.atomic():
        from django.utils import timezone
        recues_map = {item['ligne_id']: item['quantite_recue'] for item in lignes_recues}

        for ligne in transfert.lignes.select_related('produit').all():
            qte_recue = recues_map.get(ligne.pk, ligne.quantite_envoyee)
            ligne.quantite_recue = qte_recue
            ligne.save(update_fields=['quantite_recue'])

            mvt = entree_stock(
                depot=transfert.depot_destination,
                produit=ligne.produit,
                quantite=qte_recue,
                utilisateur=utilisateur,
                reference_doc=transfert.numero,
                motif=f"Transfert depuis {transfert.depot_source.code}",
            )
            mvt.type_mouvement = MouvementStock.TypeMouvement.TRANSFERT_ARRIVEE
            mvt.transfert = transfert
            mvt.save(update_fields=['type_mouvement', 'transfert'])

        transfert.statut = TransfertStock.Statut.RECU
        transfert.date_reception = timezone.now()
        transfert.utilisateur_reception = utilisateur
        transfert.save(update_fields=['statut', 'date_reception', 'utilisateur_reception'])
        return transfert
