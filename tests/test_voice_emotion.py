"""
MemoAi — Tests : Voice Emotion Service
=======================================
Couvre :
  - classify_voice_emotion() sans modèle → retour gracieux (available=False)
  - _extract_features() avec librosa si disponible
  - Entraînement démo + inférence end-to-end (si librosa installé)
  - Champs Django AIAnalysis (voice_emotion, voice_emotion_score, …)
  - Propriétés AIAnalysis.voice_emotion_data / label / percent
  - Parsing des noms de fichiers RAVDESS et CREMA-D
  - Présence obligatoire du disclaimer dans chaque réponse
"""

import numpy as np
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _librosa_available() -> bool:
    try:
        import librosa  # noqa: F401
        return True
    except ImportError:
        return False


def _make_silent_wav(duration_s: float = 1.0, sr: int = 22050) -> bytes:
    """Génère un fichier WAV silencieux en mémoire (sans dépendances audio)."""
    import struct
    import wave
    import io

    n_frames = int(sr * duration_s)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # 16-bit
        wf.setframerate(sr)
        wf.writeframes(b'\x00' * n_frames * 2)
    return buf.getvalue()


def _make_sine_wav(freq: float = 440.0, duration_s: float = 1.5, sr: int = 22050) -> bytes:
    """Génère un fichier WAV avec une sinusoïde (signal non-silencieux)."""
    import wave
    import io
    import struct
    import math

    n_frames = int(sr * duration_s)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        samples = [
            int(32767 * math.sin(2 * math.pi * freq * i / sr))
            for i in range(n_frames)
        ]
        wf.writeframes(struct.pack(f'<{n_frames}h', *samples))
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Service sans modèle entraîné
# ─────────────────────────────────────────────────────────────────────────────

class TestVoiceEmotionServiceNoModel:
    """Tests qui fonctionnent même sans librosa ni modèle entraîné."""

    def setup_method(self):
        # Réinitialiser le cache du modèle entre chaque test
        import ai.services.voice_emotion_service as ve
        ve._VOICE_MODEL = None
        ve._VOICE_MODEL_NAME = None

    def test_no_audio_returns_unavailable(self):
        from ai.services.voice_emotion_service import classify_voice_emotion
        result = classify_voice_emotion(audio_bytes=None, audio_path=None)
        assert result['available'] is False
        assert result['voice_emotion'] is None
        assert result['voice_emotion_score'] is None
        assert 'disclaimer' in result
        assert len(result['disclaimer']) > 10

    def test_disclaimer_always_present(self):
        from ai.services.voice_emotion_service import classify_voice_emotion
        result = classify_voice_emotion(audio_bytes=b'fake')
        # disclaimer doit toujours être présent, quelle que soit la situation
        assert 'disclaimer' in result
        assert isinstance(result['disclaimer'], str)
        assert len(result['disclaimer']) > 0

    def test_result_keys_complete(self):
        from ai.services.voice_emotion_service import classify_voice_emotion
        result = classify_voice_emotion(audio_bytes=None)
        required_keys = {
            'voice_emotion', 'voice_emotion_score', 'voice_probabilities',
            'uncertain', 'model_used', 'disclaimer', 'label', 'emoji',
            'color', 'available',
        }
        assert required_keys.issubset(result.keys()), (
            f"Clés manquantes : {required_keys - result.keys()}"
        )

    def test_unavailable_uncertain_is_true(self):
        from ai.services.voice_emotion_service import classify_voice_emotion
        result = classify_voice_emotion(audio_bytes=None)
        assert result['uncertain'] is True

    def test_disclaimer_in_french_by_default(self):
        from ai.services.voice_emotion_service import classify_voice_emotion
        result = classify_voice_emotion(audio_bytes=None, lang='fr')
        # Vérifie que le disclaimer contient au moins un mot français
        assert any(word in result['disclaimer'].lower()
                   for word in ['estimation', 'indicative', 'modèles', 'modeles', 'anglais'])


# ─────────────────────────────────────────────────────────────────────────────
# 2. Extraction de features (nécessite librosa)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _librosa_available(), reason="librosa non installé")
class TestFeatureExtraction:

    def test_extract_features_sine_wav(self):
        from ai.services.voice_emotion_service import _extract_features
        wav_bytes = _make_sine_wav(duration_s=1.5)
        features = _extract_features(wav_bytes, mime_type='audio/wav')
        assert features is not None, "Les features ne doivent pas être None pour un signal valide"
        assert features.shape == (364,), f"Vecteur attendu de 364 dim, obtenu : {features.shape}"
        assert not np.isnan(features).any(), "Les features ne doivent pas contenir de NaN"
        assert not np.isinf(features).any(), "Les features ne doivent pas contenir d'infini"

    def test_extract_features_silent_wav(self):
        from ai.services.voice_emotion_service import _extract_features
        # Un signal silencieux devrait retourner None (trop court ou sans énergie)
        # OU un vecteur valide selon la longueur — les deux sont acceptables
        wav_bytes = _make_silent_wav(duration_s=1.0)
        features = _extract_features(wav_bytes, mime_type='audio/wav')
        # On accepte None (signal trop court) OU un vecteur valide
        if features is not None:
            assert features.shape == (364,)
            assert np.isfinite(features).all()

    def test_extract_features_too_short(self):
        from ai.services.voice_emotion_service import _extract_features
        # 0.1s < 0.5s minimum → doit retourner None
        wav_bytes = _make_silent_wav(duration_s=0.1)
        features = _extract_features(wav_bytes, mime_type='audio/wav')
        assert features is None, "Un audio trop court devrait retourner None"

    def test_extract_features_invalid_bytes(self):
        from ai.services.voice_emotion_service import _extract_features
        features = _extract_features(b'not_audio_data', mime_type='audio/wav')
        assert features is None, "Des bytes invalides doivent retourner None"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Entraînement démo + inférence end-to-end (nécessite librosa)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _librosa_available(), reason="librosa non installé")
class TestVoiceEmotionEndToEnd:

    @pytest.fixture(scope="class")
    def demo_model(self, tmp_path_factory):
        """Entraîne un mini modèle démo et le sauvegarde dans un dossier temporaire."""
        import joblib
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        from ai.ml.train_voice_emotion import generate_demo_features, EMOTION_CLASSES

        tmp_models = tmp_path_factory.mktemp("models")
        Xd, yd = generate_demo_features(n_samples=280, seed=0)

        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=50, random_state=0, n_jobs=1)),
        ])
        pipeline.fit(Xd, yd)

        model_path = tmp_models / "voice_emotion_rf.joblib"
        joblib.dump(pipeline, model_path, compress=1)
        return model_path, pipeline

    def test_classify_with_demo_model(self, demo_model):
        import ai.services.voice_emotion_service as ve_mod
        model_path, pipeline = demo_model

        # Injecter le modèle démo dans le cache
        ve_mod._VOICE_MODEL = pipeline
        ve_mod._VOICE_MODEL_NAME = "voice_emotion_rf_demo"

        wav_bytes = _make_sine_wav(duration_s=1.5)
        result = ve_mod.classify_voice_emotion(audio_bytes=wav_bytes, mime_type='audio/wav')

        # Avec un modèle chargé, available doit être True
        assert result['available'] is True
        assert result['voice_emotion'] in [
            'neutre', 'joie', 'tristesse', 'colere', 'peur', 'degout', 'surprise'
        ]
        assert 0.0 <= result['voice_emotion_score'] <= 1.0
        assert isinstance(result['uncertain'], bool)
        assert 'disclaimer' in result
        assert len(result['voice_probabilities']) > 0

        # Reset cache
        ve_mod._VOICE_MODEL = None
        ve_mod._VOICE_MODEL_NAME = None

    def test_probabilities_sum_to_one(self, demo_model):
        import ai.services.voice_emotion_service as ve_mod
        _, pipeline = demo_model

        ve_mod._VOICE_MODEL = pipeline
        ve_mod._VOICE_MODEL_NAME = "voice_emotion_rf_demo"

        wav_bytes = _make_sine_wav(freq=880.0, duration_s=2.0)
        result = ve_mod.classify_voice_emotion(audio_bytes=wav_bytes, mime_type='audio/wav')

        if result['available']:
            total = sum(result['voice_probabilities'].values())
            assert abs(total - 1.0) < 0.05, f"Somme des probas = {total} (attendu ≈ 1.0)"

        ve_mod._VOICE_MODEL = None
        ve_mod._VOICE_MODEL_NAME = None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Champs Django AIAnalysis
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAIAnalysisVoiceEmotionFields:

    def _create_entry_and_analysis(self, voice_emotion='joie', score=0.72, uncertain=False):
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from ai.models import AIAnalysis
        from journal.models import JournalEntry

        User = get_user_model()
        user = User.objects.create_user(
            email=f"voice_{voice_emotion}@test.com",
            password="testpass123",
            first_name="Test",
        )
        entry = JournalEntry.objects.create(
            user=user,
            title="Test vocal",
            content="Contenu de test",
            entry_date=timezone.now().date(),
        )
        analysis = AIAnalysis.objects.create(
            entry=entry,
            emotion='neutre',
            emotion_score=0.5,
            emotion_status='completed',
            voice_emotion=voice_emotion,
            voice_emotion_score=score,
            voice_emotion_uncertain=uncertain,
            voice_emotion_status='completed',
        )
        return entry, analysis

    def test_voice_emotion_fields_saved(self):
        _, analysis = self._create_entry_and_analysis('joie', 0.78, False)
        analysis.refresh_from_db()
        assert analysis.voice_emotion == 'joie'
        assert abs(analysis.voice_emotion_score - 0.78) < 0.001
        assert analysis.voice_emotion_uncertain is False
        assert analysis.voice_emotion_status == 'completed'

    def test_voice_emotion_percent_property(self):
        _, analysis = self._create_entry_and_analysis('tristesse', 0.63)
        assert analysis.voice_emotion_percent == 63

    def test_voice_emotion_percent_none_when_no_score(self):
        _, analysis = self._create_entry_and_analysis()
        analysis.voice_emotion_score = None
        analysis.save(update_fields=['voice_emotion_score'])
        analysis.refresh_from_db()
        assert analysis.voice_emotion_percent is None

    def test_voice_emotion_label_property(self):
        _, analysis = self._create_entry_and_analysis('colere', 0.55)
        assert analysis.voice_emotion_label == 'Colère'

    def test_voice_emotion_data_has_required_keys(self):
        _, analysis = self._create_entry_and_analysis('peur', 0.40)
        data = analysis.voice_emotion_data
        for key in ('key', 'label', 'emoji', 'color', 'description'):
            assert key in data, f"Clé manquante dans voice_emotion_data : {key}"

    def test_voice_emotion_uncertain_defaults_true(self):
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from ai.models import AIAnalysis
        from journal.models import JournalEntry

        User = get_user_model()
        user = User.objects.create_user(
            email="voice_default@test.com",
            password="testpass123",
            first_name="Test",
        )
        entry = JournalEntry.objects.create(
            user=user,
            title="Default test",
            content="Contenu",
            entry_date=timezone.now().date(),
        )
        analysis = AIAnalysis.objects.create(entry=entry)
        assert analysis.voice_emotion_uncertain is True  # défaut

    def test_voice_emotion_status_default_pending(self):
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from ai.models import AIAnalysis
        from journal.models import JournalEntry

        User = get_user_model()
        user = User.objects.create_user(
            email="voice_pending@test.com",
            password="testpass123",
            first_name="Test",
        )
        entry = JournalEntry.objects.create(
            user=user,
            title="Pending test",
            content="Contenu",
            entry_date=timezone.now().date(),
        )
        analysis = AIAnalysis.objects.create(entry=entry)
        assert analysis.voice_emotion_status == 'pending'


# ─────────────────────────────────────────────────────────────────────────────
# 5. Parsing des noms de fichiers RAVDESS et CREMA-D
# ─────────────────────────────────────────────────────────────────────────────

class TestDatasetParsing:

    def test_ravdess_happy(self):
        from ai.ml.train_voice_emotion import parse_ravdess_label
        assert parse_ravdess_label("03-01-03-01-01-01-12.wav") == "joie"

    def test_ravdess_angry(self):
        from ai.ml.train_voice_emotion import parse_ravdess_label
        assert parse_ravdess_label("03-01-05-01-02-01-08.wav") == "colere"

    def test_ravdess_neutral(self):
        from ai.ml.train_voice_emotion import parse_ravdess_label
        assert parse_ravdess_label("03-01-01-01-01-01-01.wav") == "neutre"

    def test_ravdess_calm_maps_to_neutre(self):
        from ai.ml.train_voice_emotion import parse_ravdess_label
        assert parse_ravdess_label("03-01-02-01-01-01-01.wav") == "neutre"

    def test_ravdess_fearful(self):
        from ai.ml.train_voice_emotion import parse_ravdess_label
        assert parse_ravdess_label("03-01-06-01-01-01-01.wav") == "peur"

    def test_ravdess_surprised(self):
        from ai.ml.train_voice_emotion import parse_ravdess_label
        assert parse_ravdess_label("03-01-08-01-01-01-01.wav") == "surprise"

    def test_ravdess_invalid_returns_none(self):
        from ai.ml.train_voice_emotion import parse_ravdess_label
        assert parse_ravdess_label("random_name.wav") is None

    def test_cremad_happy(self):
        from ai.ml.train_voice_emotion import parse_cremad_label
        assert parse_cremad_label("1001_DFA_HAP_XX.wav") == "joie"

    def test_cremad_angry(self):
        from ai.ml.train_voice_emotion import parse_cremad_label
        assert parse_cremad_label("1001_IEO_ANG_HI.wav") == "colere"

    def test_cremad_neutral(self):
        from ai.ml.train_voice_emotion import parse_cremad_label
        assert parse_cremad_label("1001_IEO_NEU_XX.wav") == "neutre"

    def test_cremad_fearful(self):
        from ai.ml.train_voice_emotion import parse_cremad_label
        assert parse_cremad_label("1001_IEO_FEA_XX.wav") == "peur"

    def test_cremad_disgust(self):
        from ai.ml.train_voice_emotion import parse_cremad_label
        assert parse_cremad_label("1001_IEO_DIS_XX.wav") == "degout"

    def test_cremad_invalid_returns_none(self):
        from ai.ml.train_voice_emotion import parse_cremad_label
        assert parse_cremad_label("random.wav") is None

    def test_cremad_unknown_code_returns_none(self):
        from ai.ml.train_voice_emotion import parse_cremad_label
        assert parse_cremad_label("1001_DFA_XYZ_XX.wav") is None


# ─────────────────────────────────────────────────────────────────────────────
# 6. Génération de features synthétiques (sans librosa)
# ─────────────────────────────────────────────────────────────────────────────

class TestDemoFeatureGeneration:

    def test_generate_demo_shape(self):
        from ai.ml.train_voice_emotion import generate_demo_features, EMOTION_CLASSES
        X, y = generate_demo_features(n_samples=140)
        per_class = 140 // len(EMOTION_CLASSES)
        expected_total = per_class * len(EMOTION_CLASSES)
        assert X.shape == (expected_total, 364)
        assert len(y) == expected_total

    def test_all_emotions_represented(self):
        from ai.ml.train_voice_emotion import generate_demo_features, EMOTION_CLASSES
        _, y = generate_demo_features(n_samples=700)
        represented = set(y)
        for emo in EMOTION_CLASSES:
            assert emo in represented, f"Émotion manquante dans le dataset démo : {emo}"

    def test_features_finite(self):
        from ai.ml.train_voice_emotion import generate_demo_features
        X, _ = generate_demo_features(n_samples=70)
        assert np.isfinite(X).all(), "Les features synthétiques contiennent des valeurs non finies"

    def test_demo_reproducible(self):
        from ai.ml.train_voice_emotion import generate_demo_features
        X1, y1 = generate_demo_features(seed=99)
        X2, y2 = generate_demo_features(seed=99)
        np.testing.assert_array_equal(X1, X2)
        assert y1 == y2
