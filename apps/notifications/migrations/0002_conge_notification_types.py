from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='type_notification',
            field=models.CharField(
                choices=[
                    ('rupture_stock', 'Rupture de stock'),
                    ('seuil_stock', 'Seuil de stock atteint'),
                    ('ecart_caisse', 'Écart de caisse'),
                    ('mission_litige', 'Mission en litige'),
                    ('taux_change_expire', 'Taux de change expiré'),
                    ('echeance_client', 'Échéance client'),
                    ('transfert_valide', 'Transfert de stock reçu'),
                    ('conge_demande', 'Demande de congé'),
                    ('conge_approuve', 'Congé approuvé'),
                    ('conge_rejete', 'Congé refusé'),
                    ('maintenance_vehicule', 'Maintenance véhicule'),
                    ('commande_fournisseur', 'Commande fournisseur'),
                    ('info', 'Information'),
                ],
                default='info', max_length=30, verbose_name='Type',
            ),
        ),
    ]
