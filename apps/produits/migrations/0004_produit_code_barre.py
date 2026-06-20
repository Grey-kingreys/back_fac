# Ajout du champ code_barre sur Produit (scan code-barres → recherche produit).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produits', '0003_alter_commandefournisseur_numero_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='produit',
            name='code_barre',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Code-barres physique (EAN/UPC) scanné pour retrouver le produit',
                max_length=64,
                verbose_name='Code-barres',
            ),
        ),
    ]
