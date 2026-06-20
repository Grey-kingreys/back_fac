# Generated manually — lien Paiement → CompteMobileMoney (paiement de vente par mobile money)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
        ('ventes', '0003_alter_commande_numero_alter_devis_numero_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='paiement',
            name='compte_mobile_money',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='paiements_ventes',
                to='finance.comptemobilemoney',
                help_text='Compte crédité pour un paiement Orange Money / MTN Money',
                verbose_name='Compte Mobile Money',
            ),
        ),
    ]
