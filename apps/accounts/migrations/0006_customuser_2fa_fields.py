from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_customuser_first_login_done_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='two_factor_enabled',
            field=models.BooleanField(default=False, verbose_name='2FA activée'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='two_factor_method',
            field=models.CharField(
                blank=True,
                default='',
                help_text="'totp' (app Authy/Authenticator) ou 'email' (code par email).",
                max_length=10,
                verbose_name='Méthode 2FA',
            ),
        ),
        migrations.AddField(
            model_name='customuser',
            name='totp_secret',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Secret TOTP'),
        ),
    ]
