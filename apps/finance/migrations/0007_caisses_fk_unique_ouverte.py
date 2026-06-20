import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Caisses physiques & zone : OneToOne → ForeignKey.

    Une caisse fermée reste en base définitivement (règle universelle §1) ; il faut
    donc pouvoir créer une NOUVELLE caisse pour la période suivante une fois la
    précédente fermée. Le OneToOne l'interdisait (400 « existe déjà »).
    On le remplace par une contrainte unique PARTIELLE : au plus une caisse
    OUVERTE par dépôt / par zone à la fois.
    """

    dependencies = [
        ('companies', '0001_initial'),
        ('finance', '0006_configurationcaisse'),
    ]

    operations = [
        migrations.AlterField(
            model_name='caissephysique',
            name='depot',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='caisses',
                to='companies.depot',
                verbose_name='Dépôt',
            ),
        ),
        migrations.AlterField(
            model_name='caissezone',
            name='zone',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='caisses',
                to='companies.zone',
                verbose_name='Zone',
            ),
        ),
        migrations.AddConstraint(
            model_name='caissephysique',
            constraint=models.UniqueConstraint(
                condition=models.Q(('statut', 'ouverte')),
                fields=('depot',),
                name='unique_caisse_ouverte_par_depot',
            ),
        ),
        migrations.AddConstraint(
            model_name='caissezone',
            constraint=models.UniqueConstraint(
                condition=models.Q(('statut', 'ouverte')),
                fields=('zone',),
                name='unique_caisse_ouverte_par_zone',
            ),
        ),
    ]
