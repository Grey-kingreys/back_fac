from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_caissephysique_devise_caisseentreprise_caissezone_and_more'),
    ]

    operations = [
        # CaissePhysique : statut + fermee_le
        migrations.AddField(
            model_name='caissephysique',
            name='statut',
            field=models.CharField(
                choices=[('ouverte', 'Ouverte'), ('fermee', 'Fermée définitivement')],
                default='ouverte',
                max_length=10,
                verbose_name='Statut',
            ),
        ),
        migrations.AddField(
            model_name='caissephysique',
            name='fermee_le',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fermée le'),
        ),
        # CaisseZone : statut + fermee_le
        migrations.AddField(
            model_name='caissezone',
            name='statut',
            field=models.CharField(
                choices=[('ouverte', 'Ouverte'), ('fermee', 'Fermée définitivement')],
                default='ouverte',
                max_length=10,
                verbose_name='Statut',
            ),
        ),
        migrations.AddField(
            model_name='caissezone',
            name='fermee_le',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fermée le'),
        ),
        # TransactionMobileMoney : reference_operateur obligatoire
        migrations.AlterField(
            model_name='transactionmobilemoney',
            name='reference_operateur',
            field=models.CharField(
                help_text='ID de transaction obligatoire (Orange Money / MTN Money)',
                max_length=100,
                verbose_name='Référence opérateur',
            ),
        ),
    ]
