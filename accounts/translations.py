"""
MemoAi — Centralized Bilingual Translation Catalog (French & English)
Provides dictionary lookup and fallback mechanisms for platform templates and views.
"""

TRANSLATIONS = {
    "fr": {
        # Navigation & Shell
        "nav_journal": "Journal",
        "nav_memories": "Souvenirs",
        "nav_persons": "Personnes",
        "nav_insights": "Insights",
        "nav_tags": "Tags",
        "nav_search_placeholder": "Rechercher...",
        "nav_new": "Nouveau",
        "nav_new_entry": "Nouvelle entrée",
        "nav_my_profile": "Mon profil",
        "nav_preferences": "Préférences",
        "nav_notifications": "Notifications",
        "nav_logout": "Déconnexion",
        "nav_home": "Accueil",
        "nav_about": "À propos",
        "nav_contact": "Contact",
        "nav_login": "Connexion",
        "nav_register": "S'inscrire",
        "toggle_theme": "Basculer le thème",

        # Common Actions
        "save": "Enregistrer",
        "cancel": "Annuler",
        "edit": "Modifier",
        "delete": "Supprimer",
        "back": "Retour",
        "confirm": "Confirmer",
        "close": "Fermer",
        "search": "Rechercher",
        "filter": "Filtrer",
        "loading": "Chargement...",
        "all": "Tout",

        # Preferences Page
        "prefs_eyebrow": "COMPTE & PARAMÈTRES",
        "prefs_title": "Préférences",
        "prefs_member_since": "Membre depuis",
        "prefs_nav_personal": "Informations personnelles",
        "prefs_nav_appearance": "Apparence",
        "prefs_nav_ai": "Intelligence Artificielle",
        "prefs_nav_notifications": "Notifications & Rappels",
        "prefs_nav_security": "Sécurité & Mot de passe",

        # Appearance Card
        "prefs_appearance_title": "Apparence",
        "prefs_appearance_desc": "Personnalisez le rendu visuel et l'ergonomie de votre journal",
        "prefs_theme_label": "Thème de l'interface",
        "prefs_theme_desc": "Aperçu direct en cliquant sur une option",
        "theme_light": "Clair",
        "theme_dark": "Sombre",
        "theme_system": "Système",
        "prefs_lang_label": "Langue",
        "prefs_lang_desc": "Langue principale des menus et analyses",
        "prefs_lang_fr": "Français (France)",
        "prefs_lang_en": "English (US)",
        "prefs_motion_label": "Réduire les animations",
        "prefs_motion_desc": "Désactive les transitions lourdes et les rotations 3D",

        # AI Card
        "prefs_ai_title": "Intelligence Artificielle",
        "prefs_ai_desc": "Contrôlez les modèles IA appliqués à vos écrits et médias",
        "prefs_ai_summaries_label": "Résumés automatiques (Gemini)",
        "prefs_ai_summaries_desc": "Génère automatiquement une synthèse claire de vos pensées quotidiennes",
        "prefs_ai_sentiment_label": "Analyse des sentiments et émotions",
        "prefs_ai_sentiment_desc": "Détecte vos humeurs et tendances émotionnelles au fil du temps (RoBERTa)",
        "prefs_ai_image_label": "Génération d'illustrations (Stable Diffusion)",
        "prefs_ai_image_desc": "Génère des visuels d'accompagnement inspirés de vos récits",
        "prefs_ai_face_label": "Reconnaissance faciale (Visages)",
        "prefs_ai_face_desc": "Identifie automatiquement vos proches et vos amis sur les photos importées",
        "prefs_ai_autodelete_label": "Auto-suppression des biométries",
        "prefs_ai_autodelete_desc": "Supprime définitivement les empreintes faciales calculées après identification",

        # Notifications Card
        "prefs_notif_title": "Notifications & Rappels",
        "prefs_notif_desc": "Configurez vos alertes quotidiennes et vos rétrospectives",
        "prefs_notif_daily_label": "Rappel quotidien d'écriture",
        "prefs_notif_daily_desc": "Une notification douce pour vous encourager à écrire chaque jour",
        "prefs_notif_time_label": "Heure du rappel quotidien",
        "prefs_notif_weekly_label": "Rétrospective hebdomadaire",
        "prefs_notif_weekly_desc": "Recevez un récapitulatif de vos temps forts chaque dimanche soir",
        "prefs_notif_monthly_label": "Bilan mensuel complet",
        "prefs_notif_monthly_desc": "Une synthèse globale de vos humeurs, personnes croisées et thèmes du mois",
        "prefs_notif_email_label": "Notifications par email",
        "prefs_notif_email_desc": "Recevez les résumés et alertes importantes directement dans votre boîte mail",

        # Sticky Save Bar
        "prefs_sticky_hint": "Cliquez sur enregistrer pour valider tous vos choix.",
        "prefs_save_btn": "Enregistrer les préférences",

        # Security Card
        "prefs_sec_title": "Sécurité du compte",
        "prefs_sec_desc": "Modifiez votre mot de passe pour protéger vos souvenirs privés",
        "prefs_sec_current_pwd": "Mot de passe actuel",
        "prefs_sec_new_pwd": "Nouveau mot de passe",
        "prefs_sec_pwd_hint": "Minimum 8 caractères avec majuscule et chiffre",
        "prefs_sec_confirm_pwd": "Confirmer le nouveau mot de passe",
        "prefs_sec_submit_btn": "Mettre à jour le mot de passe",

        # Feedback Messages
        "msg_prefs_saved": "Vos préférences ont été enregistrées avec succès !",
        "msg_pwd_updated": "Votre mot de passe a été modifié avec succès !",
        "msg_pwd_incorrect": "Le mot de passe actuel est incorrect.",
        "msg_pwd_too_short": "Le nouveau mot de passe doit comporter au moins 8 caractères.",
        "msg_pwd_mismatch": "Les deux nouveaux mots de passe ne correspondent pas.",
        "msg_lang_changed": "Langue mise à jour en Français.",

        # Tags Page
        "tags_title": "Tags & Catégories",
        "tags_subtitle": "Organisez vos pensées, voyages et souvenirs par thématiques colorées",
        "tags_new_btn": "Nouveau tag",
        "tags_search_placeholder": "Filtrer les tags...",
        "tags_color_label": "Couleur du tag",
        "tags_name_label": "Nom du tag",
        "tags_desc_label": "Description (optionnelle)",
        "tags_empty": "Aucun tag trouvé.",
        "tags_create_title": "Créer un nouveau tag",
        "tags_edit_title": "Modifier le tag",

        # Journal Page
        "journal_title": "Mon Journal",
        "journal_subtitle": "Votre espace de réflexion et de souvenirs privés",
        "journal_all": "Toutes les entrées",
        "journal_favorites": "Favoris",
        "journal_drafts": "Brouillons",
        "journal_published": "Publiés",
        "journal_new_entry": "Nouvelle entrée",
        "journal_empty": "Aucune entrée trouvée.",
    },
    "en": {
        # Navigation & Shell
        "nav_journal": "Journal",
        "nav_memories": "Memories",
        "nav_persons": "People",
        "nav_insights": "Insights",
        "nav_tags": "Tags",
        "nav_search_placeholder": "Search...",
        "nav_new": "New",
        "nav_new_entry": "New entry",
        "nav_my_profile": "My profile",
        "nav_preferences": "Preferences",
        "nav_notifications": "Notifications",
        "nav_logout": "Log out",
        "nav_home": "Home",
        "nav_about": "About",
        "nav_contact": "Contact",
        "nav_login": "Log in",
        "nav_register": "Sign up",
        "toggle_theme": "Toggle theme",

        # Common Actions
        "save": "Save",
        "cancel": "Cancel",
        "edit": "Edit",
        "delete": "Delete",
        "back": "Back",
        "confirm": "Confirm",
        "close": "Close",
        "search": "Search",
        "filter": "Filter",
        "loading": "Loading...",
        "all": "All",

        # Preferences Page
        "prefs_eyebrow": "ACCOUNT & SETTINGS",
        "prefs_title": "Preferences",
        "prefs_member_since": "Member since",
        "prefs_nav_personal": "Personal Information",
        "prefs_nav_appearance": "Appearance",
        "prefs_nav_ai": "Artificial Intelligence",
        "prefs_nav_notifications": "Notifications & Reminders",
        "prefs_nav_security": "Security & Password",

        # Appearance Card
        "prefs_appearance_title": "Appearance",
        "prefs_appearance_desc": "Customize the visual display and user experience of your journal",
        "prefs_theme_label": "Interface theme",
        "prefs_theme_desc": "Live preview by clicking any option",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "theme_system": "System",
        "prefs_lang_label": "Language",
        "prefs_lang_desc": "Primary language for menus, prompts and analytics",
        "prefs_lang_fr": "Français (France)",
        "prefs_lang_en": "English (US)",
        "prefs_motion_label": "Reduce animations",
        "prefs_motion_desc": "Disables heavy transitions and 3D rotations",

        # AI Card
        "prefs_ai_title": "Artificial Intelligence",
        "prefs_ai_desc": "Control AI models applied to your notes and media",
        "prefs_ai_summaries_label": "Automatic summaries (Gemini)",
        "prefs_ai_summaries_desc": "Automatically generates clear summaries of your daily reflections",
        "prefs_ai_sentiment_label": "Sentiment and emotion analysis",
        "prefs_ai_sentiment_desc": "Tracks your mood trends and emotional patterns over time (RoBERTa)",
        "prefs_ai_image_label": "Illustration generation (Stable Diffusion)",
        "prefs_ai_image_desc": "Generates artistic companion visuals inspired by your journal stories",
        "prefs_ai_face_label": "Facial recognition (Faces)",
        "prefs_ai_face_desc": "Automatically detects and recognizes friends and loved ones in photos",
        "prefs_ai_autodelete_label": "Auto-delete biometric data",
        "prefs_ai_autodelete_desc": "Permanently deletes calculated facial embeddings after indexing",

        # Notifications Card
        "prefs_notif_title": "Notifications & Reminders",
        "prefs_notif_desc": "Configure daily writing reminders and retrospectives",
        "prefs_notif_daily_label": "Daily writing reminder",
        "prefs_notif_daily_desc": "A gentle prompt encouraging you to write every day",
        "prefs_notif_time_label": "Daily reminder time",
        "prefs_notif_weekly_label": "Weekly recap",
        "prefs_notif_weekly_desc": "Receive a digest of your week highlights every Sunday evening",
        "prefs_notif_monthly_label": "Monthly review",
        "prefs_notif_monthly_desc": "A comprehensive overview of your moods, people and monthly themes",
        "prefs_notif_email_label": "Email notifications",
        "prefs_notif_email_desc": "Receive important recaps and alerts directly in your inbox",

        # Sticky Save Bar
        "prefs_sticky_hint": "Click save to apply all your chosen preferences.",
        "prefs_save_btn": "Save preferences",

        # Security Card
        "prefs_sec_title": "Account security",
        "prefs_sec_desc": "Change your password to keep your personal journal safe",
        "prefs_sec_current_pwd": "Current password",
        "prefs_sec_new_pwd": "New password",
        "prefs_sec_pwd_hint": "Minimum 8 characters with uppercase and digit",
        "prefs_sec_confirm_pwd": "Confirm new password",
        "prefs_sec_submit_btn": "Update password",

        # Feedback Messages
        "msg_prefs_saved": "Your preferences have been successfully saved!",
        "msg_pwd_updated": "Your password was successfully updated!",
        "msg_pwd_incorrect": "Current password is incorrect.",
        "msg_pwd_too_short": "New password must contain at least 8 characters.",
        "msg_pwd_mismatch": "New passwords do not match.",
        "msg_lang_changed": "Language switched to English.",

        # Tags Page
        "tags_title": "Tags & Categories",
        "tags_subtitle": "Organize your thoughts, travels and memories with vibrant colored tags",
        "tags_new_btn": "New tag",
        "tags_search_placeholder": "Filter tags...",
        "tags_color_label": "Tag color",
        "tags_name_label": "Tag name",
        "tags_desc_label": "Description (optional)",
        "tags_empty": "No tags found.",
        "tags_create_title": "Create new tag",
        "tags_edit_title": "Edit tag",

        # Journal Page
        "journal_title": "My Journal",
        "journal_subtitle": "Your private sanctuary for thoughts and memories",
        "journal_all": "All entries",
        "journal_favorites": "Favorites",
        "journal_drafts": "Drafts",
        "journal_published": "Published",
        "journal_new_entry": "New entry",
        "journal_empty": "No entries found.",
    }
}


class TranslationProxy:
    """
    Template-friendly translation dictionary.
    Supports attribute access (t.nav_journal) and dict access (t['nav_journal']).
    If key is missing, falls back to French, then to the key itself.
    """
    def __init__(self, lang="fr"):
        self.lang = "en" if str(lang).lower().startswith("en") else "fr"
        self._current_dict = TRANSLATIONS.get(self.lang, TRANSLATIONS["fr"])
        self._fallback_dict = TRANSLATIONS["fr"]

    def __getitem__(self, key):
        return self._current_dict.get(key, self._fallback_dict.get(key, key))

    def __getattr__(self, key):
        return self._current_dict.get(key, self._fallback_dict.get(key, key))

    def get(self, key, default=None):
        return self._current_dict.get(key, self._fallback_dict.get(key, default or key))

    def __contains__(self, key):
        return key in self._current_dict or key in self._fallback_dict


# French to English direct lookup mapping for inline text
FRENCH_TO_ENGLISH_MAP = {
    "Journal": "Journal",
    "Souvenirs": "Memories",
    "Personnes": "People",
    "Insights": "Insights",
    "Tags": "Tags",
    "Rechercher...": "Search...",
    "Nouveau": "New",
    "+ Nouveau": "+ New",
    "Nouvelle entrée": "New entry",
    "Mon profil": "My profile",
    "Préférences": "Preferences",
    "Notifications": "Notifications",
    "Déconnexion": "Log out",
    "Accueil": "Home",
    "À propos": "About",
    "Contact": "Contact",
    "Connexion": "Log in",
    "S'inscrire": "Sign up",
    "Apparence": "Appearance",
    "Thème de l'interface": "Interface theme",
    "Clair": "Light",
    "Sombre": "Dark",
    "Système": "System",
    "Langue": "Language",
    "Langue principale des menus et analyses": "Primary language for menus and analytics",
    "Réduire les animations": "Reduce animations",
    "Désactive les transitions lourdes et les rotations 3D": "Disables heavy transitions and 3D effects",
    "Intelligence Artificielle": "Artificial Intelligence",
    "Contrôlez les modèles IA appliqués à vos écrits et médias": "Control AI models applied to your notes and media",
    "Résumés automatiques (Gemini)": "Automatic summaries (Gemini)",
    "Analyse des sentiments et émotions": "Sentiment and emotion analysis",
    "Génération d'illustrations (Stable Diffusion)": "Illustration generation (Stable Diffusion)",
    "Reconnaissance faciale (Visages)": "Facial recognition (Faces)",
    "Auto-suppression des biométries": "Auto-delete biometric data",
    "Notifications & Rappels": "Notifications & Reminders",
    "Configurez vos alertes quotidiennes et vos rétrospectives": "Configure daily alerts and retrospectives",
    "Rappel quotidien d'écriture": "Daily writing reminder",
    "Heure du rappel quotidien": "Daily reminder time",
    "Heure du rappel": "Reminder time",
    "Rétrospective hebdomadaire": "Weekly recap",
    "Bilan mensuel complet": "Monthly review",
    "Bilan mensuel": "Monthly review",
    "Notifications par email": "Email notifications",
    "Sécurité du compte": "Account security",
    "Sécurité & Mot de passe": "Security & Password",
    "Informations personnelles": "Personal Information",
    "Compte & Paramètres": "Account & Settings",
    "COMPTE & PARAMÈTRES": "ACCOUNT & SETTINGS",
    "Enregistrer les préférences": "Save preferences",
    "Cliquez sur enregistrer pour valider tous vos choix.": "Click save to apply your changes.",
    "Modifier votre mot de passe pour protéger vos souvenirs privés": "Change your password to keep your memories safe",
    "Mot de passe actuel": "Current password",
    "Nouveau mot de passe": "New password",
    "Confirmer le nouveau mot de passe": "Confirm new password",
    "Mettre à jour le mot de passe": "Update password",
    "Membre depuis": "Member since",
    "Toutes les entrées": "All entries",
    "Favoris": "Favorites",
    "Brouillons": "Drafts",
    "Publiés": "Published",
    "Modifier": "Edit",
    "Supprimer": "Delete",
    "Annuler": "Cancel",
    "Enregistrer": "Save",
    "Retour": "Back",
}


def translate_text(text, target_lang="fr"):
    """Translates a French phrase to English if target_lang is 'en'."""
    if not text:
        return text
    if str(target_lang).lower().startswith("en"):
        return FRENCH_TO_ENGLISH_MAP.get(str(text).strip(), text)
    return text
