import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import Role

User = get_user_model()


class Command(BaseCommand):
    help = 'Crée un super administrateur à partir des variables d\'environnement'

    def handle(self, *args, **options):
        email = os.getenv('SUPERADMIN_EMAIL', 'superadmin@example.com')
        password = os.getenv('SUPERADMIN_PASSWORD', 'SuperAdmin123!')

        # Vérifier si le super admin existe déjà
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'Super admin avec l\'email {email} existe déjà.')
            )
            return

        # Créer le super admin
        try:
            superadmin = User.objects.create_superuser(
                email=email,
                password=password,
                first_name='Super',
                last_name='Admin',
                role=Role.SUPERADMIN,
                is_active=True,
                first_login_done=True,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Super admin créé avec succès!\n'
                    f'  Email: {email}\n'
                    f'  Rôle: {superadmin.get_role_display()}'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Erreur lors de la création du super admin: {str(e)}')
            )
