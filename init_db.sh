#!/bin/bash

# Script d'initialisation de la base de données
# Exécute les migrations et crée le super admin

set -e

echo "🔄 Exécution des migrations..."
python manage.py migrate

echo "👤 Création du super admin..."
python manage.py seed_superadmin

echo "✅ Base de données initialisée avec succès!"
