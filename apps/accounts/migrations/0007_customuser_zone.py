from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_customuser_2fa_fields'),
        ('companies', '0004_gestionnaire_depot'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='zone',
            field=models.ForeignKey(
                blank=True,
                help_text='Renseigné pour les Superviseurs (responsable de zone).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='superviseurs',
                to='companies.zone',
                verbose_name='Zone',
            ),
        ),
    ]
