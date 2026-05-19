@echo off
REM Script d'initialisation de la base de données pour Windows
REM Exécute les migrations et crée le super admin

echo 🔄 Execution des migrations...
python manage.py migrate

echo 👤 Creation du super admin...
python manage.py seed_superadmin

echo ✅ Base de donnees initialisee avec succes!
pause
