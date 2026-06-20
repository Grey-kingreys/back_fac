import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0002_document_commande_document_mission_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Presence : géolocalisation du pointage ──────────────────────────
        migrations.AddField(
            model_name='presence',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Latitude du pointage'),
        ),
        migrations.AddField(
            model_name='presence',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Longitude du pointage'),
        ),
        migrations.AddField(
            model_name='presence',
            name='distance_m',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Distance au point de référence (m)'),
        ),
        migrations.AddField(
            model_name='presence',
            name='dans_perimetre',
            field=models.BooleanField(blank=True, help_text='True si le pointage est dans le rayon autorisé autour du dépôt/zone.', null=True, verbose_name='Dans le périmètre'),
        ),
        migrations.AddField(
            model_name='presence',
            name='reference_geo',
            field=models.CharField(blank=True, choices=[('depot', 'Dépôt'), ('zone', 'Zone'), ('aucune', 'Aucune référence')], max_length=10, verbose_name='Point de référence'),
        ),
        # ── Conge : traçabilité demande + décision ──────────────────────────
        migrations.AddField(
            model_name='conge',
            name='demande_par',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conges_demandes', to=settings.AUTH_USER_MODEL, verbose_name='Demandé par'),
        ),
        migrations.AddField(
            model_name='conge',
            name='motif_traitement',
            field=models.TextField(blank=True, help_text="Commentaire de l'admin/superviseur à l'approbation ou au refus.", verbose_name='Motif de la décision'),
        ),
        migrations.AddField(
            model_name='conge',
            name='traite_le',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Traité le'),
        ),
    ]
