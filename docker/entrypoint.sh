#!/bin/sh
# docker/entrypoint.sh — gestion_backend

set -e

# Flags pilotés par .env (défauts = comportement PROD sûr)
RUN_MAKEMIGRATIONS=${RUN_MAKEMIGRATIONS:-false}
RUN_SEED_DEMO=${RUN_SEED_DEMO:-false}

echo "========================================"
echo " Gestion Intégrée Multi-Sites — Démarrage"
echo "========================================"

# ── 1. Attente PostgreSQL ─────────────────────────────────────────────
echo "[1] Attente de PostgreSQL..."
until python -c "
import psycopg, os, sys
db_url = os.getenv('DATABASE_URL')
try:
    if db_url:
        conn = psycopg.connect(db_url)
    else:
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

# ── 2. Makemigrations (LOCAL UNIQUEMENT) ──────────────────────────────
if [ "$RUN_MAKEMIGRATIONS" = "true" ]; then
  echo "[2] Génération des migrations (mode dev)..."
  python manage.py makemigrations companies --no-input || echo "  [WARN] companies : pas de changement"
  python manage.py makemigrations accounts  --no-input || echo "  [WARN] accounts : pas de changement"
else
  echo "[2] makemigrations ignoré (prod — migrations déjà commitées)"
fi

# ── 3. Migrate (TOUJOURS) ─────────────────────────────────────────────
echo "[3] Application des migrations..."
python manage.py migrate --no-input

# ── 4. Seed Super Admin (idempotent, TOUJOURS) ────────────────────────
echo "[4] Création du super admin (si nécessaire)..."
python manage.py seed_superadmin || echo "  [INFO] Super admin déjà existant ou erreur"

# ── 5. Seed données de démo (LOCAL UNIQUEMENT) ────────────────────────
if [ "$RUN_SEED_DEMO" = "true" ]; then
  echo "[5] Seed données de démo (mode dev)..."
  python manage.py seed_demo_data || echo "  [WARN] Erreur lors du seed démo"
else
  echo "[5] seed_demo_data ignoré (prod)"
fi

# ── 6. Collectstatic (TOUJOURS) ───────────────────────────────────────
echo "[6] Collectstatic..."
python manage.py collectstatic --no-input --clear

echo "========================================"
echo " Démarrage du serveur..."
echo "========================================"

exec "$@"