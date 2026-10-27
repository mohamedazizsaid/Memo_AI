# 🧠 Modèles de Machine Learning — MemoAI

Ce dossier regroupe les 3 modèles d'intelligence artificielle entraînés localement et intégrés à la plateforme **MemoAI**. Ces modèles complètent les grands modèles de langage (LLM Gemini / Hugging Face) en apportant une inférence rapide, souveraine et reproductible directement dans le backend Django.

---

## 📊 Tableau Récapitulatif des 3 Modèles

| Modèle | Domaine / Mission | Algorithme | Dataset & Source | Fichier Modèle |
| :--- | :--- | :--- | :--- | :--- |
| **1. Text Emotion Classifier** | Détection des 7 émotions fondamentales dans les écrits du journal intime | **TF-IDF + LinearSVC Calibré** (`CalibratedClassifierCV`) | [JusteLeo/French-emotion (HuggingFace)](https://huggingface.co/datasets/JusteLeo/French-emotion) + Augmentation Journal intime | `models/emotion_svm.joblib` |
| **2. Voice Emotion Classifier** | Analyse des émotions dans la voix (notes vocales & enregistrements audio) | **Random Forest Acoustique** (`StandardScaler` + `RandomForestClassifier`) | [CREMA-D (GitHub)](https://github.com/CheyneyComputerScience/CREMA-D) & [RAVDESS (Zenodo)](https://zenodo.org/records/1188976) | `models/voice_emotion_rf.joblib` |
| **3. Churn & Retention Predictor** | Prédiction du risque d'abandon et réengagement proactif automatique | **Pipeline Scaler + Random Forest** (`class_weight='balanced'`) | Dataset comportemental MemoAI (2 500 cohortes synthétiques + réelles) : `data/churn_dataset.csv` | `models/churn_model.joblib` |

---

## 1. Modèle de Classification des Émotions Textuelles

### 🎯 Ce que fait le modèle
Ce modèle analyse le texte d'une entrée de journal intime en langue française et classe l'état émotionnel de l'utilisateur parmi **7 émotions fondamentales** :
- `joie`, `tristesse`, `colere`, `peur`, `surprise`, `degout`, `neutre`.

L'émotion détectée est affichée sous forme d'insigne et d'icône vectorielle sur chaque entrée de journal et alimente les graphiques de suivi du bien-être et de l'humeur.

### ⚙️ Algorithme utilisé
- **Vectorisation Textuelle** : `TfidfVectorizer` (n-grams de 1 à 2 mots, pondération sous-linéaire TF `sublinear_tf=True`, liste dédiée de stop words français adaptée à la rédaction intime).
- **Classifieur** : Support Vector Machine linéaire (`LinearSVC`, $C=1.0$).
- **Calibration probabiliste** : Encapsulé dans un `CalibratedClassifierCV` (méthode de Platt / régression sigmoïde à 5 plis de validation croisée) permettant de retourner des probabilités réelles et étalonnées pour chaque émotion.

### 🔗 Dataset & Liens
- **Source principale** : [Dataset Hugging Face `JusteLeo/French-emotion`](https://huggingface.co/datasets/JusteLeo/French-emotion) (corpus francophone d'expressions émotionnelles annotées).
- **Augmentation métier** : Corpus interne spécifique au journal intime (`DIARY_AUGMENTATION`) couvrant le vocabulaire introspectif, les confidences de fin de journée et les nuances poétiques.

### 📁 Fichiers associés
- **Script d'entraînement** : [`ai/ml/train_baseline.py`](file:///c:/Users/user/Desktop/eng/3eme/django/MemoAi/MemoAI/ai/ml/train_baseline.py)
- **Modèle sérialisé** : `ai/ml/models/emotion_svm.joblib`
- **Commande d'entraînement** :
  ```powershell
  .venv\Scripts\python.exe ai/ml/train_baseline.py
  ```

---

## 2. Modèle de Reconnaissance des Émotions Vocales

### 🎯 Ce que fait le modèle
Lorsqu'un utilisateur enregistre une note vocale ou joint un fichier audio à son journal intime, ce modèle extrait la signature spectrale et prosodique de la voix pour inférer l'émotion exprimée à l'oral, sans dépendre exclusivement de la transcription textuelle.

### ⚙️ Algorithme utilisé
- **Extraction des Caractéristiques Acoustiques (`librosa`)** :
  - **MFCCs** (Mel-Frequency Cepstral Coefficients, 40 coefficients : moyenne + variance)
  - **Chroma STFT** (distribution des hauteurs tonales)
  - **Mel Spectrogram** (énergie par bande fréquentielle)
  - **Spectral Contrast** (contraste harmonique)
  - **Zero-Crossing Rate** (taux de passage par zéro pour la texture sonore)
  - **Tonnetz** (centroïdes tonals / dynamique émotionnelle)
- **Classifieur** : `RandomForestClassifier` (200 arbres de décision, équilibrage automatique des classes `class_weight='balanced'`) précédé d'un `StandardScaler` (alternative SVM RBF supportée).

### 🔗 Datasets & Liens
1. **CREMA-D** (*Crowd-sourced Emotional Multimodal Actors Dataset*) :
   - Dépôt officiel : [GitHub CheyneyComputerScience/CREMA-D](https://github.com/CheyneyComputerScience/CREMA-D)
   - Contenu : 7 442 clips vocaux annotés avec différentes intensités émotionnelles.
2. **RAVDESS** (*Ryerson Audio-Visual Database of Emotional Speech and Song*) :
   - Dépôt officiel : [Zenodo Record 1188976](https://zenodo.org/records/1188976)
   - Contenu : 24 acteurs professionnels enregistrés avec émotions contrôlées (calme, joie, tristesse, colère, peur, surprise, dégoût).

### 📁 Fichiers associés
- **Script d'entraînement** : [`ai/ml/train_voice_emotion.py`](file:///c:/Users/user/Desktop/eng/3eme/django/MemoAi/MemoAI/ai/ml/train_voice_emotion.py)
- **Modèle sérialisé** : `ai/ml/models/voice_emotion_rf.joblib`
- **Commande d'entraînement rapide** :
  ```powershell
  .venv\Scripts\python.exe ai/ml/train_voice_emotion.py --demo
  ```

---

## 3. Modèle de Prédiction du Risque d'Abandon (Churn & Rétention)

### 🎯 Ce que fait le modèle
Ce modèle de Machine Learning prédictif surveille l'engagement des utilisateurs afin d'identifier ceux qui risquent de quitter la plateforme ou de décrocher de leur routine d'écriture.

Il alimente une tâche planifiée **Celery Beat** qui s'exécute chaque **dimanche à minuit** pour :
1. Détecter les utilisateurs inactifs ou dont l'activité chute fortement.
2. Envoyer automatiquement un email personnalisé et inspirant pour les réengager (avec un sujet chaleureux et des suggestions d'écriture).
3. Créer une notification in-app d'encouragement.
4. Tracer l'action dans le journal d'audit administrateur (`AdminLog`).

### ⚙️ Algorithme utilisé
- **Pipeline** : `StandardScaler` + `RandomForestClassifier` (150 estimateurs, `max_depth=10`, `min_samples_split=4`, `class_weight='balanced'`).
- **Inférence probabiliste** : `predict_proba()` fournit la probabilité de churn ($0$ à $1$) classée en 3 niveaux de risque :
  - **Élevé** ($\ge 70\%$)
  - **Modéré** ($45\% - 70\%$)
  - **Faible** ($< 45\%$)
- **Interprétabilité** : Fournit les motifs explicatifs du diagnostic (ex. *« Aucune note rédigée depuis 18 jours »*, *« Baisse d'activité de 85% »*).

### 📈 Features d'interaction analysées (Top facteurs d'importance) :
1. `days_since_last_entry` : Nombre de jours depuis la dernière note de journal (importance : **20.89%**)
2. `days_since_last_login` : Nombre de jours depuis la dernière connexion (importance : **20.48%**)
3. `activity_drop_ratio` : Vitesse d'effondrement de l'activité sur les 30 derniers jours (importance : **19.27%**)
4. `entries_last_30d` : Volume de notes créées le mois dernier (importance : **13.81%**)
5. `entries_last_7d` : Activité sur la dernière semaine (importance : **8.57%**)
6. `ai_usage_rate` : Degré d'adoption des fonctionnalités IA (importance : **6.35%**)
7. `media_count` : Nombre de médias et photos attachés (importance : **4.86%**)
8. `has_audio_entries` : Utilisation des enregistrements vocaux (importance : **1.81%**)
9. `negative_mood_ratio` : Taux d'humeurs difficiles récentes (anxiété, tristesse, stress)

### 🔗 Dataset & Liens
- **Fichier du jeu de données** : [`ai/ml/data/churn_dataset.csv`](file:///c:/Users/user/Desktop/eng/3eme/django/MemoAi/MemoAI/ai/ml/data/churn_dataset.csv)
- **Générateur & Modélisation** : [`ai/ml/generate_churn_dataset.py`](file:///c:/Users/user/Desktop/eng/3eme/django/MemoAi/MemoAI/ai/ml/generate_churn_dataset.py)
  - Construit sur **2 500 profils** équilibrés représentant les cohortes comportementales typiques des applications SaaS et de journal intime (Power Users, Journalistes réguliers, Nouveaux comptes actifs, Utilisateurs en décrochage, Comptes inactifs).
  - Fusionne dynamiquement les statistiques des vrais utilisateurs issus de la base PostgreSQL / Django.

### 📁 Fichiers associés
- **Extraction des variables** : [`ai/ml/churn_features.py`](file:///c:/Users/user/Desktop/eng/3eme/django/MemoAi/MemoAI/ai/ml/churn_features.py)
- **Générateur du dataset** : [`ai/ml/generate_churn_dataset.py`](file:///c:/Users/user/Desktop/eng/3eme/django/MemoAi/MemoAI/ai/ml/generate_churn_dataset.py)
- **Script d'entraînement** : [`ai/ml/train_churn_model.py`](file:///c:/Users/user/Desktop/eng/3eme/django/MemoAi/MemoAI/ai/ml/train_churn_model.py)
- **Service d'inférence** : [`ai/ml/churn_service.py`](file:///c:/Users/user/Desktop/eng/3eme/django/MemoAi/MemoAI/ai/ml/churn_service.py)
- **Modèle sérialisé** : `ai/ml/models/churn_model.joblib`
- **Tâche Celery Beat** : `ai.tasks.check_churn_risk_and_reengage_users` (chaque dimanche minuit)
- **Commande de test et d'audit** :
  ```powershell
  # Diagnostic de tous les utilisateurs sans envoi d'email
  .venv\Scripts\python.exe manage.py run_churn_check --dry-run --show-all

  # Exécution réelle
  .venv\Scripts\python.exe manage.py run_churn_check --threshold 0.55
  ```
