import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('companies', '0001_initial'),
        ('finance', '0005_depenseoperationnelle_deleted_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigurationCaisse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duree_session_jours', models.PositiveIntegerField(default=1, help_text='Période de la caisse journalière / session caissier. Défaut : 1 jour.', verbose_name="Durée d'une session caissier (jours)")),
                ('duree_caisse_depot_jours', models.PositiveIntegerField(default=30, help_text="Période de consolidation d'une caisse dépôt. Défaut : 30 jours (1 mois).", verbose_name="Durée d'une période de caisse dépôt (jours)")),
                ('duree_caisse_zone_jours', models.PositiveIntegerField(default=90, help_text="Période de consolidation d'une caisse zone. Défaut : 90 jours (3 mois).", verbose_name="Durée d'une période de caisse zone (jours)")),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='configuration_caisse', to='companies.company', verbose_name='Entreprise')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='configurations_caisse_modifiees', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Configuration des caisses',
                'verbose_name_plural': 'Configurations des caisses',
            },
        ),
    ]
