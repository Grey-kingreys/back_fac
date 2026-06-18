from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logistique', '0004_mission_qr_code_vehicule_annee_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='mission',
            name='type_mission',
            field=models.CharField(
                choices=[
                    ('transfert', 'Transfert inter-dépôt'),
                    ('livraison', 'Livraison client'),
                    ('enlevement', 'Enlèvement fournisseur'),
                ],
                default='transfert',
                max_length=20,
                verbose_name='Type de mission',
            ),
        ),
    ]
