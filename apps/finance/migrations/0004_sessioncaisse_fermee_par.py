from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_caissephysique_statut_caissezone_statut_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='sessioncaisse',
            name='fermee_par',
            field=models.ForeignKey(
                blank=True,
                help_text='Traçabilité : qui a fermé la session (caissier, admin ou superviseur).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sessions_fermees',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Fermée par',
            ),
        ),
    ]
