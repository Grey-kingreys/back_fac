from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Aligne le modèle Depot sur le skill CDC :
    - Supprime gestionnaire (FK inversé — le gestionnaire passe par User.depot)
    - Ajoute latitude/longitude propres au dépôt (marqueur GPS distinct de sa zone)
    """

    dependencies = [
        ('companies', '0004_gestionnaire_depot'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='depot',
            name='gestionnaire',
        ),
        migrations.AddField(
            model_name='depot',
            name='latitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text='Latitude du dépôt (ex: 9.537500)',
                max_digits=9,
                null=True,
                verbose_name='Latitude',
            ),
        ),
        migrations.AddField(
            model_name='depot',
            name='longitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text='Longitude du dépôt (ex: -13.677300)',
                max_digits=9,
                null=True,
                verbose_name='Longitude',
            ),
        ),
    ]
