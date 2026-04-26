#!/bin/sh
# docker/entrypoint.sh — gestion_backend

set -e

echo "========================================"
echo " Gestion Intégrée Multi-Sites — Démarrage"
echo "========================================"

# ── 1. Attente PostgreSQL ─────────────────────────────────────────────
echo "[1/4] Attente de PostgreSQL..."
until python -c "
import psycopg, os, sys
try:
    conn = psycopg.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', '5432'),
    )
    conn.close()
    print('  PostgreSQL pret')
except Exception as e:
    print(f'  Pas encore pret : {e}')
    sys.exit(1)
"; do
  sleep 2
done

# ── 2. Makemigrations ─────────────────────────────────────────────────
echo "[2/4] Génération des migrations..."
python manage.py makemigrations companies --no-input || echo "  [WARN] companies : pas de changement"
python manage.py makemigrations accounts  --no-input || echo "  [WARN] accounts : pas de changement"
# Ajouter ici les apps au fur et à mesure des releases
# python manage.py makemigrations produits  --no-input || echo "  [WARN] produits : pas de changement"

# ── 3. Migrate ────────────────────────────────────────────────────────
echo "[3/4] Application des migrations..."
python manage.py migrate --no-input

# ── 4. Collectstatic ─────────────────────────────────────────────────
echo "[4/4] Collectstatic..."
python manage.py collectstatic --no-input --clear

echo "========================================"
echo " Démarrage du serveur..."
echo " URL : http://localhost:8001"
echo " Swagger : http://localhost:8001/api/schema/docs/"
echo "========================================"

exec "$@"