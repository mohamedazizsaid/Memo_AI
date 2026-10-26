import pytest
from ai.services.emotion_service import classify_emotion, EMOTION_META
from ai.models import AIAnalysis
from journal.models import JournalEntry
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
class TestEmotionClassifier:

    def test_classify_happy_text(self):
        result = classify_emotion("Je suis tellement heureux aujourd'hui, c'est une excellente nouvelle !")
        assert result['emotion'] in EMOTION_META
        assert result['emotion'] == 'joie'
        assert result['score'] > 0.5
        assert result['label'] == 'Joie'
        assert result['emoji'] == '😊'

    def test_classify_sad_text(self):
        result = classify_emotion("Je me sens triste et abattu, tout me paraît lourd et douloureux.")
        assert result['emotion'] == 'tristesse'
        assert result['label'] == 'Tristesse'
        assert result['emoji'] == '😢'

    def test_classify_anger_text(self):
        result = classify_emotion("Je suis furieux contre cette injustice, c'est intolérable et inadmissible !")
        assert result['emotion'] == 'colere'
        assert result['label'] == 'Colère'
        assert result['emoji'] == '😠'

    def test_journal_entry_emotion_properties(self):
        user = User.objects.create_user(email="emotion@example.com", password="secretpassword123", first_name="Emotion")
        entry = JournalEntry.objects.create(
            user=user,
            title="Journée inoubliable",
            content="Quelle magnifique journée passée au soleil avec mes amis les plus chers !",
            entry_date=timezone.now().date(),
        )
        ai_analysis = AIAnalysis.objects.create(
            entry=entry,
            emotion='joie',
            emotion_score=0.96,
            emotion_status='completed'
        )

        # Verification through JournalEntry properties
        assert entry.detected_emotion == 'joie'
        assert entry.detected_emotion_data['label'] == 'Joie'
        assert entry.detected_emotion_percent == 96
        assert ai_analysis.emotion_percent == 96
        assert ai_analysis.emotion_label == 'Joie'
