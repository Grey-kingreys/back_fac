import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logistique', '0006_alter_mission_numero_and_more'),
        ('ventes', '0003_alter_commande_numero_alter_devis_numero_and_more'),
        ('produits', '0003_alter_commandefournisseur_numero_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mission',
            name='depot_depart',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='missions_depart',
                to='companies.depot',
                verbose_name='Dépôt départ',
            ),
        ),
        migrations.AlterField(
            model_name='mission',
            name='depot_arrivee',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='missions_arrivee',
                to='companies.depot',
                verbose_name='Dépôt arrivée',
            ),
        ),
        migrations.AddField(
            model_name='mission',
            name='client',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='missions',
                to='ventes.client',
                verbose_name='Client (livraison)',
            ),
        ),
        migrations.AddField(
            model_name='mission',
            name='fournisseur',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='missions',
                to='produits.fournisseur',
                verbose_name='Fournisseur (enlèvement)',
            ),
        ),
    ]
