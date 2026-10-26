"""
MemoAi — Bespoke Brand Iconography System
Custom vector icons for emotions, moods, and brand identity.
Replaces generic operating system emojis (Windows/Apple/Android) with
tailored, scalable SVG icons aligned with MemoAi's organic, impressionistic palette.
"""

from django.utils.safestring import mark_safe

# Custom SVGs for all 10 user moods
MOOD_SVGS = {
    # Amazing: Sparkling radiant eyes with a joyful, uplifting smile
    'amazing': '''<svg class="memo-icon memo-icon--mood memo-icon--amazing" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M7.5 9.5L8.5 7.5L9.5 9.5L11.5 10.5L9.5 11.5L8.5 13.5L7.5 11.5L5.5 10.5L7.5 9.5Z" fill="currentColor"/>
  <path d="M14.5 9.5L15.5 7.5L16.5 9.5L18.5 10.5L16.5 11.5L15.5 13.5L14.5 11.5L12.5 10.5L14.5 9.5Z" fill="currentColor"/>
  <path d="M8 15.5C9.2 17.2 10.5 17.8 12 17.8C13.5 17.8 14.8 17.2 16 15.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Good: Warm, content smiling face with soft eyes and gentle smile
    'good': '''<svg class="memo-icon memo-icon--mood memo-icon--good" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M8 10C8.5 9.2 9.5 9 10 9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M14 9C14.5 9 15.5 9.2 16 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M8.5 14.5C9.5 16.2 10.7 16.8 12 16.8C13.3 16.8 14.5 16.2 15.5 14.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Excited: Radiant celebratory eyes with joyous open laugh
    'excited': '''<svg class="memo-icon memo-icon--mood memo-icon--excited" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M7.5 9.5C8.2 8.5 9.8 8.5 10.5 9.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M13.5 9.5C14.2 8.5 15.8 8.5 16.5 9.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M8 14C8 14 9.5 17.5 12 17.5C14.5 17.5 16 14 16 14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="12" y1="2" x2="12" y2="0.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="3.5" y1="4.5" x2="2.2" y2="3.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="20.5" y1="4.5" x2="21.8" y2="3.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Grateful: Gentle serene eyes with hands/lotus contour and peaceful grace
    'grateful': '''<svg class="memo-icon memo-icon--mood memo-icon--grateful" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M8 10.5C9 10 10 10.5 10 11.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M14 11.5C14 10.5 15 10 16 10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M9.5 15C10.5 16 11.2 16.2 12 16.2C12.8 16.2 13.5 16 14.5 15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M12 6.5C11.5 5 12 4.2 12 4.2C12 4.2 12.5 5 12 6.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
</svg>''',

    # Neutral: Calm, reflective horizontal balance line
    'neutral': '''<svg class="memo-icon memo-icon--mood memo-icon--neutral" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="9" cy="10" r="1.2" fill="currentColor"/>
  <circle cx="15" cy="10" r="1.2" fill="currentColor"/>
  <line x1="8.5" y1="15" x2="15.5" y2="15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Tired: Peaceful closed crescent eyes with a resting breath
    'tired': '''<svg class="memo-icon memo-icon--mood memo-icon--tired" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M7.5 10.5C8.5 11.5 9.5 11.5 10.5 10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M13.5 10.5C14.5 11.5 15.5 11.5 16.5 10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="12" cy="15.5" r="1.5" stroke="currentColor" stroke-width="1.4"/>
</svg>''',

    # Stressed: Tense diagonal brow with resolute mouth line
    'stressed': '''<svg class="memo-icon memo-icon--mood memo-icon--stressed" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="7.5" y1="9.5" x2="10.5" y2="10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="16.5" y1="9.5" x2="13.5" y2="10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M8.5 15.5L10.2 14.5L12 15.5L13.8 14.5L15.5 15.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
</svg>''',

    # Anxious: Concerned eyes with a soft worried arc
    'anxious': '''<svg class="memo-icon memo-icon--mood memo-icon--anxious" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="9" cy="10.5" r="1.3" fill="currentColor"/>
  <circle cx="15" cy="10.5" r="1.3" fill="currentColor"/>
  <path d="M7.5 8C8.5 7.5 9.5 8 10 8.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
  <path d="M16.5 8C15.5 7.5 14.5 8 14 8.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
  <path d="M9 15.5C10.2 14.5 13.8 14.5 15 15.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Sad: Downcast melancholic eyes with gentle tender mouth
    'sad': '''<svg class="memo-icon memo-icon--mood memo-icon--sad" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="9" cy="10" r="1.2" fill="currentColor"/>
  <circle cx="15" cy="10" r="1.2" fill="currentColor"/>
  <path d="M15.5 15.8C14.5 14.4 13.3 13.8 12 13.8C10.7 13.8 9.5 14.4 8.5 15.8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Angry: Sharp determined brow lines with firm mouth
    'angry': '''<svg class="memo-icon memo-icon--mood memo-icon--angry" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="7.5" y1="8.5" x2="10.5" y2="10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="16.5" y1="8.5" x2="13.5" y2="10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="9.2" cy="11.5" r="1.1" fill="currentColor"/>
  <circle cx="14.8" cy="11.5" r="1.1" fill="currentColor"/>
  <path d="M9 16C10.2 15 13.8 15 15 16" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',
}


# Custom SVGs for the 7 core AI emotions
EMOTION_SVGS = {
    # Joie: Radiant sunburst halo with harmonious smile
    'joie': '''<svg class="memo-icon memo-icon--emotion memo-icon--joie" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.6"/>
  <path d="M8 9.5C8.8 8.8 9.8 8.8 10.5 9.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M13.5 9.5C14.2 8.8 15.2 8.8 16 9.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M8 14C9.2 16.2 10.5 16.8 12 16.8C13.5 16.8 14.8 16.2 16 14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Tristesse: Gentle melancholic curve with subtle tear drop accent
    'tristesse': '''<svg class="memo-icon memo-icon--emotion memo-icon--tristesse" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.6"/>
  <circle cx="8.5" cy="10" r="1.2" fill="currentColor"/>
  <circle cx="15.5" cy="10" r="1.2" fill="currentColor"/>
  <path d="M15.5 15.5C14.5 14.2 13.3 13.6 12 13.6C10.7 13.6 9.5 14.2 8.5 15.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M16 11.5C16.8 12.5 17 13.2 16.5 13.6C16 14 15.2 13.5 15.2 12.8C15.2 12.2 15.7 11.8 16 11.5Z" fill="currentColor"/>
</svg>''',

    # Colère: Resolute angled brows with intense focus
    'colere': '''<svg class="memo-icon memo-icon--emotion memo-icon--colere" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.6"/>
  <line x1="7.5" y1="8.5" x2="10.8" y2="10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="16.5" y1="8.5" x2="13.2" y2="10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="9.2" cy="11.8" r="1.1" fill="currentColor"/>
  <circle cx="14.8" cy="11.8" r="1.1" fill="currentColor"/>
  <line x1="8.5" y1="15.5" x2="15.5" y2="15.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Peur: Apprehensive wide eyes with trembling gentle wave
    'peur': '''<svg class="memo-icon memo-icon--emotion memo-icon--peur" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.6"/>
  <circle cx="9" cy="10" r="1.8" stroke="currentColor" stroke-width="1.4"/>
  <circle cx="15" cy="10" r="1.8" stroke="currentColor" stroke-width="1.4"/>
  <path d="M9 15C10 14.5 11 15.5 12 15C13 14.5 14 15.5 15 15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Surprise: Wide-open round eyes with expressive oval mouth
    'surprise': '''<svg class="memo-icon memo-icon--emotion memo-icon--surprise" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.6"/>
  <circle cx="8.5" cy="9.5" r="1.5" fill="currentColor"/>
  <circle cx="15.5" cy="9.5" r="1.5" fill="currentColor"/>
  <ellipse cx="12" cy="15.2" rx="2.5" ry="3" stroke="currentColor" stroke-width="1.6"/>
</svg>''',

    # Dégoût: Squinted angled eyes with aversion mouth
    'degout': '''<svg class="memo-icon memo-icon--emotion memo-icon--degout" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.6"/>
  <path d="M7.5 9L10.5 11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M10.5 9L7.5 11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M13.5 9L16.5 11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M16.5 9L13.5 11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M8.5 15.5C9.5 14.2 11 16 12 15C13 14 14.5 15.5 15.5 14.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',

    # Neutre: Serene balanced composure
    'neutre': '''<svg class="memo-icon memo-icon--emotion memo-icon--neutre" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.6"/>
  <circle cx="8.5" cy="10" r="1.2" fill="currentColor"/>
  <circle cx="15.5" cy="10" r="1.2" fill="currentColor"/>
  <line x1="8.5" y1="15" x2="15.5" y2="15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>''',
}


def get_mood_svg(mood_key: str, size: int = None, extra_class: str = "") -> str:
    """Returns safe HTML string containing the bespoke SVG icon for a mood."""
    key = str(mood_key or 'neutral').strip().lower()
    raw = MOOD_SVGS.get(key, MOOD_SVGS['neutral'])
    if size:
        raw = raw.replace('<svg ', f'<svg width="{size}" height="{size}" ')
    if extra_class:
        raw = raw.replace('class="', f'class="{extra_class} ')
    return mark_safe(raw)


def get_emotion_svg(emotion_key: str, size: int = None, extra_class: str = "") -> str:
    """Returns safe HTML string containing the bespoke SVG icon for an emotion."""
    key = str(emotion_key or 'neutre').strip().lower()
    raw = EMOTION_SVGS.get(key, EMOTION_SVGS['neutre'])
    if size:
        raw = raw.replace('<svg ', f'<svg width="{size}" height="{size}" ')
    if extra_class:
        raw = raw.replace('class="', f'class="{extra_class} ')
    return mark_safe(raw)
