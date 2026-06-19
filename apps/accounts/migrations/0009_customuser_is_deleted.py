import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_alter_customuser_first_login_done'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='Supprimé'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date de suppression'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='deleted_users',
                to='accounts.customuser',
                verbose_name='Supprimé par',
            ),
        ),
    ]
