# 🚀 MemoAI — Guide de Déploiement Complet

## Vue d'ensemble de l'architecture

```
GitHub (push main)
    │
    ▼
GitHub Actions CI/CD
    ├─ Tests (pytest + DB PostgreSQL)
    ├─ Build Docker image → GitHub Container Registry (ghcr.io)
    └─ Deploy hook → Render.com
                         │
                    ┌────┴────┐
                    │  Render  │
                    │ (Docker) │
                    │ Gunicorn │
                    └────┬────┘
                         │ DATABASE_URL
                         ▼
                    ┌─────────┐
                    │ Neon DB │  (PostgreSQL serverless)
                    └─────────┘
                         +
                    ┌──────────┐
                    │Cloudinary│  (médias utilisateurs)
                    └──────────┘
```

---

## 1. 🗄️ Neon DB (PostgreSQL serverless)

### Créer la base de données

1. Va sur [console.neon.tech](https://console.neon.tech)
2. **New Project** → nom : `memoai`
3. Région : `AWS eu-central-1` (Frankfurt, proche de l'Europe)
4. Copie la **Connection string** → format :
   ```
   postgresql://memoai_user:password@ep-xxx-xxxx.neon.tech/memoai?sslmode=require
   ```

### Variables à configurer sur Render

| Variable | Valeur |
|---|---|
| `DATABASE_URL` | `postgresql://user:pass@ep-xxx.neon.tech/memoai?sslmode=require` |
| `DB_ENGINE` | `postgresql` |
| `USE_SQLITE` | `False` |

> **Note :** `DATABASE_URL` est prioritaire sur `DB_HOST/DB_NAME/...` dans notre settings.py.

---

## 2. 🌐 Render — Déploiement

### Option A — Deploy automatique via render.yaml (recommandé)

1. Va sur [render.com](https://render.com) → **New** → **Blueprint**
2. Connecte ton repo GitHub `mohamedazizsaid/Memo_AI`
3. Render détecte `render.yaml` automatiquement
4. Remplis les variables marquées `sync: false` dans le Dashboard

### Option B — Deploy manuel

1. **New** → **Web Service**
2. Source : GitHub → repo `Memo_AI`, branche `main`
3. **Runtime** : Docker
4. **Dockerfile path** : `./Dockerfile`
5. **Health check path** : `/health/`
6. **Plan** : Free (ou Starter $7/mo pour 0 spin-down)

### Variables d'environnement à renseigner dans Render

```bash
SECRET_KEY=<généré par Render ou python -c "import secrets; print(secrets.token_urlsafe(64))">
DEBUG=False
FRONTEND_URL=https://<ton-service>.onrender.com
ALLOWED_HOSTS=<ton-service>.onrender.com
CSRF_TRUSTED_ORIGINS=https://<ton-service>.onrender.com
CORS_ALLOWED_ORIGINS=https://<ton-service>.onrender.com

DATABASE_URL=postgresql://memoai_user:password@ep-xxx.neon.tech/memoai?sslmode=require
USE_SQLITE=False
DB_ENGINE=postgresql

USE_REDIS=False
CELERY_ALWAYS_EAGER=True

CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_VISION_MODEL=gemini-2.5-flash
HUGGINGFACE_API_KEY=...

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...  # App password Gmail
DEFAULT_FROM_EMAIL=MemoAI <noreply@memoai.app>

PEXELS_API_KEY=...
```

### Initialisation automatique au démarrage (Compatible Render Free Tier)

Sur le plan **Free Tier** de Render, la directive `preDeployCommand` n'est pas autorisée. 
L'initialisation automatique (migrations de base de données + création du compte administrateur) est donc intégrée directement dans la commande de démarrage `CMD` du [`Dockerfile`](file:///c:/Users/user/Desktop/eng/3eme/django/MemoAi/MemoAI/Dockerfile) :

```bash
python manage.py migrate --noinput && python manage.py seed_admin && gunicorn config.wsgi:application ...
```

> **Identifiants Admin générés par défaut :**
> - **URL du Front-Office Admin :** `https://<ton-service>.onrender.com/admin-panel/`
> - **Email :** `admin@memo.com`
> - **Mot de passe :** `admin123`
> *(Pensez à changer ce mot de passe après le premier déploiement !)*

---

## 3. 🤖 GitHub Actions CI/CD

### Secrets GitHub à configurer

Va dans ton repo → **Settings** → **Secrets and variables** → **Actions** :

| Secret | Description |
|---|---|
| `RENDER_DEPLOY_HOOK_URL` | URL depuis Render → Service → Settings → Deploy Hook |
| `DOCKERHUB_USERNAME` | (optionnel) ton username Docker Hub |

### Workflows déclenchés

| Événement | Action |
|---|---|
| Push sur `aziz` ou `develop` | ✅ Tests uniquement |
| Push sur `main` | ✅ Tests + Build Docker + Deploy Render |
| Pull Request vers `main` | ✅ Tests uniquement |

### Obtenir le Deploy Hook Render

1. Render Dashboard → ton service → **Settings**
2. Section **Deploy Hook** → copie l'URL
3. Colle-la dans GitHub Secrets comme `RENDER_DEPLOY_HOOK_URL`

---

## 4. 🐳 Docker — Stack locale complète

### Lancer tout l'environnement local

```bash
# Copier le template d'env Docker
cp .env.docker .env.docker.local  # édite avec tes vraies clés

# Démarrer tous les services
docker compose up --build

# En arrière-plan
docker compose up -d --build

# Voir les logs
docker compose logs -f web

# Stopper
docker compose down
```

### Services Docker inclus

| Service | Port | Description |
|---|---|---|
| `web` | 8000 | Django + Gunicorn |
| `nginx` | 80 | Reverse proxy + static files |
| `db` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Cache + broker Celery |
| `celery` | — | Worker async (analyse IA, transcription Whisper, face detection) |
| `celery-beat` | — | Tâches planifiées (churn hebdo dimanche 00:00, rappels quotidiens, résumés hebdo) |

### Commandes utiles Docker

```bash
# Migrations
docker compose exec web python manage.py migrate

# Seeder le compte administrateur front-office (admin@memo.com / admin123)
docker compose exec web python manage.py seed_admin

# Diagnostic du modèle de churn (analyse de risque de départ)
docker compose exec web python manage.py run_churn_check --dry-run --show-all

# Créer un superuser Django classique
docker compose exec web python manage.py createsuperuser

# Shell Django
docker compose exec web python manage.py shell

# Logs Celery & Beat
docker compose logs -f celery celery-beat

# Logs Nginx
docker compose logs -f nginx

# Rebuild uniquement le web
docker compose up -d --build web
```

---

## 5. 🔧 Nginx (local Docker)

Le fichier `nginx/nginx.conf` configure :
- **Reverse proxy** vers Gunicorn (port 8000)
- **Fichiers statiques** servis directement via volume partagé
- **Upload volumineux** : `client_max_body_size 55M` (compatible photos, audios et vidéos)
- **Timeouts étendus** : `proxy_read_timeout 180s` pour supporter l'inférence IA sans timeout HTTP 504
- **Rate limiting calibré** : 60 req/min sur `/api/` (burst 40), 120 req/min sur le tableau de bord et pages générales
- **Route dédiée `/admin-panel/`** prioritaire avec burst élevé (60) pour la réactivité du dashboard
- **Compression Gzip** automatique sur CSS, JS, JSON, XML et SVG
- **Security headers** (`X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`)

---

## 6. 🔄 Workflow recommandé (Git Flow)

```
feature/xxx → aziz (dev) → main (prod)
                 ↓              ↓
          Tests CI seul   Tests + Deploy
```

```bash
# Dev → merge vers aziz
git checkout aziz
git merge feature/ma-feature
git push origin aziz  # → CI: tests uniquement

# Production → merge vers main
git checkout main
git merge aziz
git push origin main  # → CI: tests + build + deploy Render
```

---

## 7. ✅ Checklist avant premier déploiement

- [ ] Compte Neon DB créé + `DATABASE_URL` copiée
- [ ] Compte Render créé + service configuré
- [ ] Toutes les variables d'env renseignées dans Render
- [ ] `RENDER_DEPLOY_HOOK_URL` dans GitHub Secrets
- [ ] Cloudinary configuré (stockage médias)
- [ ] Gmail App Password configuré (email)
- [ ] Branche `main` pushée → CI/CD déclenché
- [ ] `/health/` répond 200 après déploiement

---

## 8. 🛠️ Commandes de génération de clé secrète

```python
# Dans un terminal Python
import secrets
print(secrets.token_urlsafe(64))
```

Ou directement :
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```
