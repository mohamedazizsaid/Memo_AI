# MemoAi — Journal Personnel Multimodal Intelligent 🧠✨

> **MemoAi** est une plateforme web privée de journal personnel multimodal de niveau SaaS moderne, sublimée par l'intelligence artificielle générative, l'analyse des émotions et la reconnaissance visuelle et vocale.

---

## 🌟 Fonctionnalités Clés

### 1. ✍️ Journal Personnel Multimodal
- **Éditeur fluide & riche** : Rédaction avec comptage de mots en temps réel, sélecteur d'humeurs émotionnelles interactif (`🤩`, `😊`, `🎉`, `🙏`, `😐`, `😴`, `😤`, `😰`, `😢`, `😠`).
- **🎙️ Enregistreur vocal temps réel** : Visualiseur de spectre audio animé en direct sur `<canvas>` HTML5 / Web Audio API, transcription automatique par **Whisper** et analyse de sentiment.
- **📸 Galerie photo & Reconnaissance faciale** : Détection automatique des visages avec embeddings locaux respectueux de la vie privée (aucune donnée biométrique partagée).
- **📍 Géolocalisation** : Détection automatique de la position et reverse geocoding via OpenStreetMap.
- **🏷️ Tags & Catégories** : Organisation libre avec palettes de couleurs dynamiques.

### 2. 🤖 Pipeline d'Intelligence Artificielle
- **Synthèse & Rétrospective Gemini** : Résumé analytique du souvenir et synthèse hebdomadaire des émotions.
- **Analyse de Sentiment & Émotion dominante** : Modèle RoBERTa / Hugging Face évaluant la valence affective et le score de bien-être.
- **Génération d'illustrations (SDXL)** : Création d'une image artistique personnalisée reflétant l'atmosphère poétique du souvenir.
- **Résilience asynchrone** : Tâches distribuées Celery (avec mode asynchrone Redis ou synchrone/eager de développement).

### 3. 📊 Dashboard d'Insights Émotionnels
- **Trajectoire du Bien-Être** : Graphique vectoriel SVG interactif de l'évolution du sentiment (7, 30 ou 90 jours).
- **Répartition des Humeurs** : Barres de progression et statistiques de fréquence.
- **Nuage de Mots-Clés** : Thématiques récurrentes identifiées par l'IA.
- **Indicateur de Série (Streak)** : Compteur de jours consécutifs d'écriture avec flamme animée et confettis.

### 4. 👥 Galerie des Personnes
- Regroupement des souvenirs par proche identifié sur les photos.
- Renommage, fusion de profils en doublon et suppression granulaire.

### 5. 🔔 Notifications & Flashbacks Nostalgie
- **Flashback « Ce jour-là »** : Redécouvrez vos pensées consignées il y a 1 an ou plus.
- **Rappel quotidien d'écriture** et suivi des étapes de traitement IA.

---

## 🚀 Démarrage Rapide

### 🔑 Compte Démonstration
Un compte complet avec des souvenirs réels, photos, tags et analyses IA est préconfiguré :
- **Email** : `demo@memoai.local`
- **Mot de passe** : `DemoPass123!`
*(Un bouton de remplissage en 1 clic « ✨ Remplir avec un compte démo » est également disponible sur l'écran de connexion)*.

---

### 1. Démarrer le Backend (Django)
```bash
# Dans c:\Users\user\Desktop\MemoAi
.venv\Scripts\python.exe manage.py runserver 8000
```
*Le backend sera accessible sur : `http://localhost:8000`*

### 2. Démarrer le Frontend (Vite + React)
```bash
# Dans c:\Users\user\Desktop\MemoAi\frontend
npm run dev
```
*Le frontend sera accessible sur : `http://localhost:5173`*

---

## 🧪 Tests d'Intégration
Le projet dispose d'une couverture de tests automatisés vérifiant tous les flux d'API (Authentification JWT, Journal CRUD, Tags, Personnes, Notifications) :

```bash
$env:DJANGO_SETTINGS_MODULE='config.settings'
.venv\Scripts\python.exe -m pytest backend/tests/test_api.py -v
```
*(Résultat : 7 tests passés avec succès à 100%)*

---

## 🏗️ Architecture Technique

```
MemoAi/
├── backend/
│   ├── accounts/          # Authentification JWT, Profils, Préférences
│   ├── journal/           # Modèles JournalEntry, CRUD, Stats, Seeding
│   ├── media_app/         # Gestion des fichiers audio/images & Cloudinary
│   ├── ai/                # Services Gemini, Hugging Face, Celery tasks
│   ├── persons/           # Modèles Person & FaceDetection biométrique
│   ├── tags/              # Modèles Tag & EntryTag
│   ├── notifications/     # Notifications in-app & Celery Beat (Nostalgie)
│   ├── common/            # Pagination standardisée & exception handler
│   └── config/            # Paramètres Django & Celery
│
└── frontend/
    ├── src/
    │   ├── api/client.js  # Client HTTP avec auto-refresh token JWT
    │   ├── context/       # AuthContext & ThemeContext (Dark / Light)
    │   ├── components/    # Navbar, AudioRecorder, MoodSelector, EntryCard,
    │   │                  # EntryEditorModal, EntryDetailModal, AIInsightsView,
    │   │                  # PeopleView, TagsView, SettingsView, AuthModal
    │   ├── App.jsx        # Assemblage principal et navigation
    │   └── index.css      # Design System CSS moderne & glassmorphism
```
