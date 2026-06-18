from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Corrige l'isolation SaaS : Zone.code et Depot.code étaient unique=True global.
    Deux entreprises différentes ne pouvaient pas utiliser le même code.
    On remplace par des contraintes unique_together scoped à la company/zone.
    """

    dependencies = [
        ('companies', '0005_depot_gps_remove_gestionnaire'),
    ]

    operations = [
        # Zone : supprimer unique global, ajouter unique par company
        migrations.AlterField(
            model_name='zone',
            name='code',
            field=models.CharField(max_length=30, verbose_name='Code'),
        ),
        migrations.AddConstraint(
            model_name='zone',
            constraint=models.UniqueConstraint(
                fields=['company', 'code'],
                name='unique_zone_code_per_company',
            ),
        ),
        # Depot : supprimer unique global, ajouter unique par zone
        migrations.AlterField(
            model_name='depot',
            name='code',
            field=models.CharField(max_length=30, verbose_name='Code'),
        ),
        migrations.AddConstraint(
            model_name='depot',
            constraint=models.UniqueConstraint(
                fields=['zone', 'code'],
                name='unique_depot_code_per_zone',
            ),
        ),
    ]
