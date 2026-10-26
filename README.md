# MemoAi — Journal Personnel Multimodal Intelligent 🧠✨

> **MemoAi** est une plateforme web moderne de journal personnel multimodal, sublimée par l'intelligence artificielle générative (Google Gemini 2.5, Flux / Pollinations), l'analyse des émotions (RoBERTa), la transcription audio (Whisper), la reconnaissance faciale locale et respectueuse de la vie privée (`face-api.js`), ainsi qu'un studio de création vidéo de Reels.

---

## 📑 Sommaire
- [🌟 Fonctionnalités Clés](#-fonctionnalités-clés)
- [🏗️ Architecture Technique](#️-architecture-technique)
- [📦 Arborescence du Projet](#-arborescence-du-projet)
- [🚀 Démarrage Rapide](#-démarrage-rapide)
- [⚙️ Configuration & Variables d'Environnement (`.env`)](#️-configuration--variables-denvironnement-env)
- [🤖 Pipeline d'Intelligence Artificielle & Services Tiers](#-pipeline-dintelligence-artificielle--services-tiers)
- [🌐 Double Interface (Web & REST API)](#-double-interface-web--rest-api)
- [🧪 Tests Automatisés](#-tests-automatisés)
- [🛠️ Commandes Utiles de Gestion](#️-commandes-utiles-de-gestion)

---

## 🌟 Fonctionnalités Clés

### 1. ✍️ Rédaction & Éditeur Multimodal
- **Éditeur fluide & riche** : Saisie avec comptage de mots en temps réel, sélecteur d'humeurs émotionnelles interactif (`🤩`, `😊`, `🎉`, `🙏`, `😐`, `😴`, `😤`, `😰`, `😢`, `😠`).
- **🎙️ Enregistreur vocal temps réel** : Visualiseur de spectre audio animé sur `<canvas>` HTML5 / Web Audio API, transcription automatique (**Whisper**) et détection du ton.
- **📸 Bibliothèque & Photos Pexels** : Téléversement de photos personnelles et recherche intégrée d'images libres de droits via l'API Pexels.
- **📍 Lieux & Géolocalisation** : Recherche d'adresses et reverse-geocoding précis via OpenStreetMap (Nominatim).
- **🏷️ Tags & Catégories** : Organisation libre avec couleurs personnalisées et suggestions automatiques par l'IA.

### 2. 🎬 Studio Reel & Expériences Visuelles
- **🎞️ Studio de création de Reels** : Générateur de stories/vidéos courtes à partir des souvenirs, avec export vidéo fluide (Canvas / MediaRecorder), transitions, filtres et synchronisation de musique libre (Jamendo API).
- **🌌 Expérience Souvenir Immersive** : Consultation plein écran interactive des pensées et anecdotes passées.
- **🖼️ Mur de Photos (Photo Wall)** : Galerie visuelle infinie regroupant tous les clichés de vos souvenirs.

### 3. 🤖 Pipeline d'Intelligence Artificielle
- **Synthèse & Rétrospective Gemini 2.5 Flash** : Résumé analytique du souvenir, extraction des mots-clés clés et synthèse hebdomadaire du bien-être.
- **Analyse de Sentiment & Valence Affective** : Modèle RoBERTa évaluant le niveau de positivité et le score émotionnel.
- **Génération d'illustrations (Flux / Pollinations)** : Création automatique d'une image artistique personnalisée reflétant l'atmosphère du souvenir, stockée sur Cloudinary.
- **Reconnaissance faciale locale (`face-api.js`)** : Détection et identification des proches sur les photos via des descripteurs 128-d calculés localement dans le navigateur (aucune donnée biométrique partagée avec un tiers).
- **Exécution asynchrone résiliente** : Tâches distribuées Celery (support de Redis ou mode eager synchrone pour le développement).

### 4. 📊 Dashboard d'Insights Émotionnels
- **Trajectoire du Bien-Être** : Graphiques vectoriels interactifs illustrant l'évolution du sentiment (sur 7, 30 ou 90 jours).
- **Répartition des Humeurs** : Barres de progression statistiques et métriques de récurrence.
- **Nuage de Mots-Clés** : Thématiques et centres d'intérêt récurrents extraits par l'IA.
- **Compteur de Série (Streak)** : Suivi des jours consécutifs d'écriture avec flamme animée et célébration.

### 5. 👥 Galerie des Proches & Personnes
- Regroupement automatique des souvenirs par proche identifié sur les photos.
- Confirmation manuelle, renommage, fusion de profils en doublon et suppression granulaire.

### 6. 🔔 Notifications & Flashbacks Nostalgiques
- **Flashback « Ce jour-là »** : Redécouvrez vos pensées consignées il y a 1 an ou plus.
- **Rappels quotidiens programmés** : Notifications configurables selon l'heure de votre choix (tâche Celery Beat).
- **Suivi en temps réel** de l'avancement des analyses IA.

### 7. 🎨 Expérience Utilisateur & Design System Cosmos
- **Thèmes Dynamiques** : Mode Lumineux (Clair), Sombre et Système, avec persistance d'état et transitions sans scintillement.
- **Onboarding Interactif en 7 étapes** : Personnalisation complète dès l'inscription (genre, visibilité, thème, langue, confort d'animations, heure du rappel).
- **Bilingue (FR / EN)** : Prise en charge native du français et de l'anglais avec bascule instantanée.
- **Recherche Omnibox Globale** : Barre de recherche rapide dans la barre de navigation avec autocomplétion multi-entités (souvenirs, personnes, tags, photos) et page de résultats dédiée.
- **Visite Guidée Interactive (Tour)** : Découverte pas-à-pas des fonctionnalités clés de l'application.

---

## 🏗️ Architecture Technique

| Domaine | Technologies |
| --- | --- |
| **Backend & Web Shell** | Python 3.13, Django 5.x, Django Templates, Context Processors |
| **API RESTful** | Django REST Framework (DRF), JWT (`djangorestframework-simplejwt`), Throttling, Filtres |
| **Base de Données** | PostgreSQL (par défaut / production via `psycopg2`), SQLite (fallback dev) |
| **Cache & Sessions** | Redis via `django-redis` (ou LocMemCache en mode sans Redis) |
| **Tâches Asynchrones** | Celery 5.x & Celery Beat (Redis broker ou Memory eager) |
| **Stockage Média Cloud** | Cloudinary & `django-cloudinary-storage` |
| **Intelligence Artificielle** | Google Generative AI (Gemini 2.5 Flash), Hugging Face (RoBERTa & Whisper), Pollinations AI (Flux) |
| **Biométrie & Vision** | `face-api.js` (exécution côté client avec poids hébergés localement) |
| **Frontend & UI** | Vanilla JavaScript (ES6+), Canvas API, Web Audio API, Cosmos Design System (CSS Vanilla, Glassmorphism, animations fluides) |
| **Services Tiers** | OpenStreetMap / Nominatim (Géocodage), Jamendo (Musique Reels), Pexels (Photos de stock) |
| **Tests** | Pytest, Pytest-Django |

---

## 📦 Arborescence du Projet

```
MemoAI/
├── accounts/               # Authentification, profils, préférences, onboarding, i18n
│   ├── context_processors.py  # Langue et thème pré-rendus côté serveur
│   ├── models.py              # User personnalisé, UserPreferences, PasswordResetToken
│   ├── template_views.py      # Vues HTML (connexion, inscription, onboarding, profil)
│   ├── views.py               # Endpoints REST API (JWT, profils, consentement)
│   └── translations.py        # Dictionnaires de traduction bilingue (FR/EN)
│
├── journal/                # Cœur du journal personnel & studio créatif
│   ├── models.py              # JournalEntry (humeurs, coordonnées, contenu, statut IA)
│   ├── template_views.py      # Dashboard, liste, éditeur, studio Reel, souvenirs
│   ├── views.py               # Endpoints REST API CRUD journal
│   └── management/commands/   # seed_demo_data, reset_demo_data
│
├── ai/                     # Pipeline de traitement IA
│   ├── models.py              # AIAnalysis (résumé Gemini, sentiment RoBERTa, image Flux)
│   ├── services/              # Connecteurs Gemini, HuggingFace, Pollinations, Face-API
│   ├── tasks.py               # Tâches asynchrones Celery d'analyse multimodale
│   ├── template_views.py      # Vue HTML du dashboard des Insights
│   └── insight_views.py       # Endpoints REST API statistiques et tendances
│
├── persons/                # Gestion des visages et des proches
│   ├── models.py              # Person, FaceDetection (embeddings 128-d locaux)
│   ├── template_views.py      # Vues HTML de la galerie des personnes
│   └── views.py               # Endpoints REST API
│
├── tags/                   # Système de labellisation et thématiques
│   ├── models.py              # Tag, EntryTag (tags manuels et suggérés par l'IA)
│   └── template_views.py      # Vues HTML de gestion des tags
│
├── notifications/          # Notifications in-app et rappels périodiques
│   ├── models.py              # Notification (types: IA, rappel, nostalgie, série)
│   └── tasks.py               # Tâches Celery Beat (rappel quotidien, revue mensuelle)
│
├── media_app/              # Gestion des médias (photos, audios, illustrations)
│   ├── models.py              # Media (liens Cloudinary, métadonnées, miniatures)
│   └── views.py               # Téléversement et consultation média
│
├── common/                 # Utilitaires transverses
│   ├── cloud_media.py         # Client d'upload sécurisé Cloudinary
│   ├── places.py              # Client OpenStreetMap / Nominatim (autocomplétion lieux)
│   ├── pexels.py              # Client recherche de photos Pexels
│   ├── search_views.py        # Moteur de recherche globale (navbar omnibox)
│   └── models.py              # TimeStampedModel, SoftDeleteModel
│
├── config/                 # Configuration globale du projet
│   ├── settings.py            # Paramètres Django, Celery, Cloudinary, DB, IA
│   ├── urls.py                # Routage global (HTML + REST API)
│   ├── wsgi.py / asgi.py      # Points d'entrée serveurs web
│   └── celery.py              # Configuration de l'instance Celery
│
├── templates/              # Gabarits HTML Django (Design System Cosmos)
│   ├── accounts/              # login, register, onboarding, preferences, profil
│   ├── journal/               # home, list, form (éditeur), reel_studio, detail
│   ├── ai/                    # insights.html
│   ├── persons/ / tags/       # Galeries personnes et tags
│   ├── notifications/         # Centre de notifications
│   ├── search/                # Page des résultats de recherche
│   ├── partials/              # Navbar, modales, visite guidée (tour)
│   ├── base.html              # Shell principal avec gestion instantanée du thème
│   └── landing.html           # Page d'accueil marketing interactive
│
├── static/                 # Fichiers statiques servis par WhiteNoise
│   ├── css/                   # cosmos.css, app.css, auth.css, reel-studio.css...
│   ├── js/                    # onboarding.js, reel-studio.js, memory-experience.js...
│   ├── img/                   # Illustrations, tuiles de l'orbite photo
│   └── vendor/face-api/       # Librairie face-api.js et modèles de poids locaux
│
├── tests/                  # Suite de tests d'intégration automatisés
│   └── test_api.py            # Tests complets Auth, Journal, Tags, Personnes, Notifications
│
├── manage.py               # CLI d'administration Django
├── requirements.txt        # Dépendances Python
└── pytest.ini              # Configuration Pytest
```

---

## 🚀 Démarrage Rapide

### 1. Prérequis
- **Python** 3.11 ou supérieur (testé avec Python 3.13)
- **PostgreSQL** (recommandé) ou **SQLite** (inclus pour développement rapide)
- **Redis** (recommandé pour Celery asynchrone et cache, facultatif en mode eager)

### 2. Cloner et préparer l'environnement virtuel

```bash
# Cloner le dépôt
git clone https://github.com/mohamedazizsaid/Memo_AI.git
cd Memo_AI

# Créer et activer l'environnement virtuel
python -m venv .venv

# Sous Windows (PowerShell) :
.venv\Scripts\Activate.ps1
# Sous Linux / macOS :
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Configurer l'environnement
Copiez le modèle de configuration et ajustez vos clés dans le fichier `.env` :

```bash
# Créer votre fichier .env s'il n'existe pas déjà
cp .env.example .env
```
*(Voir la section suivante pour le détail des variables).*

### 4. Appliquer les migrations

```bash
python manage.py migrate
```

### 5. Peupler les données de démonstration
Une commande idempotente prépare un compte de démonstration complet avec photos, souvenirs, tags, personnes et analyses IA :

```bash
python manage.py seed_demo_data
```

**Identifiants du compte démo :**
- **Email** : `demo@memoai.local`
- **Mot de passe** : `DemoPass123!`
*(Un bouton « ✨ Remplir avec un compte démo » est également présent sur la page de connexion).*

### 6. Lancer le serveur de développement

```bash
python manage.py runserver 8000
```
L'application est immédiatement accessible sur **[http://localhost:8000](http://localhost:8000)** !

---

## ⚙️ Configuration & Variables d'Environnement (`.env`)

Toutes les configurations sont pilotées par `python-decouple` via le fichier `.env` à la racine :

| Variable | Description | Valeur par défaut |
| --- | --- | --- |
| `SECRET_KEY` | Clé secrète cryptographique Django | *(À générer pour la production)* |
| `DEBUG` | Mode débogage Django | `True` |
| `DB_ENGINE` | Moteur de base de données (`postgresql` ou `sqlite`) | `postgresql` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | Paramètres de connexion PostgreSQL | `memoai` / `localhost:5432` |
| `USE_SQLITE` | Forcer l'utilisation de SQLite en local | `False` |
| `USE_REDIS` | Activer Redis pour le cache et les sessions | `True` |
| `REDIS_URL` | URL de l'instance Redis | `redis://localhost:6379/0` |
| `CELERY_ALWAYS_EAGER` | Exécuter les tâches IA de façon synchrone (sans worker) | `False` (ou `True` si Redis est coupé) |
| `GEMINI_API_KEY` | Clé d'API Google Generative AI | *(Optionnel pour les résumés IA)* |
| `GEMINI_MODEL` | Modèle Google Gemini utilisé pour les synthèses | `gemini-2.5-flash` |
| `HUGGINGFACE_API_KEY` | Clé d'API Hugging Face | *(Optionnel pour RoBERTa & Whisper)* |
| `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | Identifiants Cloudinary pour l'hébergement des médias | *(Optionnel en local avec fallback)* |
| `PEXELS_API_KEY` | Clé API Pexels pour le sélecteur de photos libres de droits | *(Optionnel)* |
| `EMAIL_BACKEND` | Backend email (`console.EmailBackend` ou `smtp.EmailBackend`) | `django.core.mail.backends.console.EmailBackend` |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Identifiants SMTP (ex: Gmail mot de passe d'application) | `""` |

---

## 🤖 Pipeline d'Intelligence Artificielle & Services Tiers

1. **Google Gemini (`gemini-2.5-flash`)** :
   - Génère un résumé concis et bienveillant du souvenir.
   - Extrait les mots-clés thématiques et génère une réflexion émotionnelle (*mood insight*).
   - Produit une synthèse hebdomadaire des tendances émotionnelles.
2. **Hugging Face (`openai/whisper-large-v3` & `cardiffnlp/twitter-roberta-base-sentiment-latest`)** :
   - Transcription haute fidélité des enregistrements vocaux.
   - Évaluation du score de sentiment (positif, neutre, négatif) et calcul de la trajectoire affective.
3. **Pollinations AI (`flux`)** :
   - Génération d'illustrations oniriques à partir des descriptions de souvenirs (100% gratuit et sans clé d'API requise).
4. **Reconnaissance faciale locale (`face-api.js`)** :
   - Les modèles SSD Mobilenet et Face Recognition s'exécutent entièrement côté client dans le navigateur.
   - Les descripteurs vectoriels 128-d sont comparés par distance euclidienne pour regrouper automatiquement les souvenirs par personne sans exposer les visages à des API tierces.
5. **OpenStreetMap / Nominatim & Jamendo** :
   - Autocomplétion de localisation géographique sans carte bancaire ni API payante.
   - Pistes audio pour l'ambiance sonore du studio de Reels.

---

## 🌐 Double Interface (Web & REST API)

MemoAi propose une double approche unifiée :
1. **Interface Web Complète (Django Templates + Cosmos UI)** :
   - Navigation fluide, animations soignées, design system glassmorphism, responsive mobile et bureau.
   - Thème adaptatif automatique et sélecteur FR / EN sans rechargement lourd.
2. **API RESTful Standardisée (Django REST Framework)** :
   - Authentification par jetons JWT (`/api/auth/login/`, `/api/auth/token/refresh/`).
   - CRUD complet des souvenirs (`/api/entries/`), statistiques (`/api/entries/stats/`), tags (`/api/tags/`), proches (`/api/people/`) et notifications (`/api/notifications/`).
   - Réponses paginées standardisées et gestion unifiée des erreurs en format JSON.

---

## 🧪 Tests Automatisés

Le projet intègre une suite de tests d'intégration avec `pytest` et `pytest-django` :

```bash
# Lancer les tests automatisés :
$env:DJANGO_SETTINGS_MODULE="config.settings"  # Sous Windows PowerShell
pytest tests/test_api.py -v
```

**Couverture des tests :**
- Inscription, connexion et rafraîchissement de token JWT.
- Profil utilisateur et récupération des préférences.
- Création, étiquetage et calcul des statistiques de souvenirs.
- Gestion du cycle de vie des notifications in-app (non-lu, lu, marquer tout lu).
- CRUD et mise à jour des profils de personnes reconnues.

---

## 🛠️ Commandes Utiles de Gestion

```bash
# Vérifier l'intégrité de la configuration Django :
python manage.py check

# Créer un super-administrateur :
python manage.py createsuperuser

# Régénérer le compte de démonstration :
python manage.py seed_demo_data

# Migrer les fichiers médias locaux vers Cloudinary :
python manage.py migrate_local_media

# Lancer le worker Celery pour les tâches d'arrière-plan (optionnel avec Redis) :
celery -A config worker --loglevel=info

# Lancer l'ordonnanceur Celery Beat pour les rappels périodiques :
celery -A config beat --loglevel=info
```

---

<p align="center">
  Fait avec passion pour garder vos souvenirs vivants, intimes et inspirants. ✨<br>
  <strong>MemoAi © 2026</strong>
</p>
