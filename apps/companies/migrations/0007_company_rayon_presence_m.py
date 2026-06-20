from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0006_zone_code_unique_per_company_depot_code_unique_per_zone'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='rayon_presence_m',
            field=models.PositiveIntegerField(
                default=100,
                help_text=(
                    "Distance maximale autour du dépôt (ou du point central de la zone) "
                    "pour qu'un pointage de présence soit considéré « dans le périmètre »."
                ),
                verbose_name='Rayon de pointage présence (mètres)',
            ),
        ),
    ]
