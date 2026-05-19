# Seed Super Admin

Ce document explique comment créer un super administrateur pour l'application.

## Configuration

### 1. Variables d'environnement

Ajouter les variables suivantes à votre fichier `.env` :

```env
# --- Super Admin (Seed) ---
SUPERADMIN_EMAIL=votre-email@example.com
SUPERADMIN_PASSWORD=VotreMotDePasse123!
```

**Exemple de valeurs par défaut** (à modifier en production) :
```env
SUPERADMIN_EMAIL=superadmin@example.com
SUPERADMIN_PASSWORD=SuperAdmin123!
```

## Utilisation

### Option 1 : Script d'initialisation (Recommandé)

#### Sur Linux/Mac :
```bash
chmod +x init_db.sh
./init_db.sh
```

#### Sur Windows :
```cmd
init_db.bat
```

Ce script exécute automatiquement :
1. Les migrations Django
2. La création du super admin

### Option 2 : Commandes manuelles

```bash
# Exécuter les migrations
python manage.py migrate

# Créer le super admin
python manage.py seed_superadmin
```

## Résultat

Une fois exécuté, vous verrez un message de confirmation :

```
✓ Super admin créé avec succès!
  Email: superadmin@example.com
  Rôle: Super Administrateur
```

## Points importants

- ✅ Le super admin n'est créé **qu'une seule fois**
- ✅ Si un super admin avec le même email existe déjà, le script l'ignore
- ✅ Les credentials viennent du fichier `.env`
- ✅ Le super admin est automatiquement actif et peut se connecter immédiatement
- ⚠️ **En production**, changez le mot de passe par défaut !

## Connexion

Une fois créé, connectez-vous avec :
- **Email** : `SUPERADMIN_EMAIL` (de votre `.env`)
- **Mot de passe** : `SUPERADMIN_PASSWORD` (de votre `.env`)

## Réinitialisation

Si vous avez besoin de réinitialiser le super admin :

```bash
# Supprimer le super admin existant
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.filter(email='superadmin@example.com').delete()
>>> exit()

# Créer un nouveau super admin
python manage.py seed_superadmin
```
