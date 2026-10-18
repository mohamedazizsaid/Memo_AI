"""
MemoAi — Accounts Template Views
HTML interface for authentication and profile management.
"""

import logging
from django import forms
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View

from .models import UserPreferences

logger = logging.getLogger('memoai')
User = get_user_model()


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'vous@exemple.com', 'autocomplete': 'email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Votre mot de passe'})
    )


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={'placeholder': 'Minimum 8 caracteres'})
    )
    password2 = forms.CharField(
        label='Confirmer',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repetez le mot de passe'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Les mots de passe ne correspondent pas.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('Le mot de passe doit comporter au moins 8 caracteres.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            UserPreferences.objects.get_or_create(user=user)
        return user


class TemplateLoginView(View):
    """HTML login page."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('journal:home')
        return render(request, 'accounts/login.html', {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            from django.contrib.auth import authenticate
            user = authenticate(
                request,
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            if user and user.is_active:
                login(request, user)
                messages.success(request, f'Bienvenue, {user.first_name} !')
                return redirect(request.GET.get('next', 'journal:home'))
            else:
                form.add_error(None, 'Email ou mot de passe incorrect.')
        return render(request, 'accounts/login.html', {'form': form})


class TemplateRegisterView(View):
    """HTML registration page."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('journal:home')
        return render(request, 'accounts/register.html', {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Handle avatar file upload
            avatar_file = request.FILES.get('avatar_file')
            if avatar_file:
                import os
                import uuid
                from django.conf import settings
                avatars_dir = settings.MEDIA_ROOT / 'avatars'
                os.makedirs(avatars_dir, exist_ok=True)
                ext = os.path.splitext(avatar_file.name)[1].lower() or '.jpg'
                filename = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
                file_path = avatars_dir / filename
                with open(file_path, 'wb+') as destination:
                    for chunk in avatar_file.chunks():
                        destination.write(chunk)
                user.avatar = f"/media/avatars/{filename}"
                user.save(update_fields=['avatar'])
            elif request.POST.get('avatar_url'):
                user.avatar = request.POST.get('avatar_url').strip()
                user.save(update_fields=['avatar'])

            login(request, user)
            messages.success(request, f'Compte cree avec succes ! Bienvenue, {user.first_name} !')
            return redirect('journal:home')
        return render(request, 'accounts/register.html', {'form': form})


@method_decorator(login_required, name='dispatch')
class TemplateLogoutView(View):
    """Handle POST logout."""

    def post(self, request):
        logout(request)
        messages.info(request, 'Vous avez ete deconnecte.')
        return redirect('accounts:login')


@method_decorator(login_required, name='dispatch')
class TemplateProfileView(View):
    """HTML profile page."""

    def get(self, request):
        return render(request, 'accounts/profile.html', {'form': None})

    def post(self, request):
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        email = request.POST.get('email', user.email)
        if email != user.email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
            messages.error(request, 'Cet email est deja utilise.')
        else:
            user.email = email

        avatar_file = request.FILES.get('avatar_file')
        if avatar_file:
            import os
            import uuid
            from django.conf import settings
            avatars_dir = settings.MEDIA_ROOT / 'avatars'
            os.makedirs(avatars_dir, exist_ok=True)
            ext = os.path.splitext(avatar_file.name)[1].lower() or '.jpg'
            filename = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
            file_path = avatars_dir / filename
            with open(file_path, 'wb+') as destination:
                for chunk in avatar_file.chunks():
                    destination.write(chunk)
            user.avatar = f"/media/avatars/{filename}"
        elif request.POST.get('avatar'):
            user.avatar = request.POST.get('avatar')

        user.save()
        messages.success(request, 'Profil mis a jour.')
        return redirect('accounts:profile')


@method_decorator(login_required, name='dispatch')
class TemplatePreferencesView(View):
    """HTML preferences page."""

    def get(self, request):
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        return render(request, 'accounts/preferences.html', {'preferences': prefs})

    def post(self, request):
        # Handle password change if action is change_password
        if request.POST.get('action') == 'change_password':
            from django.contrib.auth import update_session_auth_hash
            current_pwd = request.POST.get('current_password', '')
            new_pwd = request.POST.get('new_password', '')
            confirm_pwd = request.POST.get('confirm_password', '')

            if not request.user.check_password(current_pwd):
                messages.error(request, 'Le mot de passe actuel est incorrect.')
                return redirect('/comptes/preferences/#securite')
            if len(new_pwd) < 8:
                messages.error(request, 'Le nouveau mot de passe doit comporter au moins 8 caracteres.')
                return redirect('/comptes/preferences/#securite')
            if new_pwd != confirm_pwd:
                messages.error(request, 'Les deux nouveaux mots de passe ne correspondent pas.')
                return redirect('/comptes/preferences/#securite')

            request.user.set_password(new_pwd)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Votre mot de passe a ete modifie avec succes !')
            return redirect('/comptes/preferences/#securite')

        # Otherwise save general preferences
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        prefs.theme = request.POST.get('theme', prefs.theme)
        new_lang = request.POST.get('language', prefs.language)
        if new_lang in ['fr', 'en']:
            prefs.language = new_lang
            request.session['django_language'] = new_lang
            from django.utils import translation
            translation.activate(new_lang)

        prefs.reduce_motion = 'reduce_motion' in request.POST

        # AI Preferences
        prefs.ai_summaries_enabled = 'ai_summaries_enabled' in request.POST
        prefs.sentiment_analysis_enabled = 'sentiment_analysis_enabled' in request.POST
        prefs.image_generation_enabled = 'image_generation_enabled' in request.POST

        # Biometric & Privacy
        new_face_consent = 'face_recognition_consent' in request.POST
        if new_face_consent and not prefs.face_recognition_consent:
            prefs.grant_face_recognition_consent()
        elif not new_face_consent and prefs.face_recognition_consent:
            prefs.revoke_face_recognition_consent()
        prefs.auto_delete_face_embeddings = 'auto_delete_face_embeddings' in request.POST

        # Notifications & Reminders
        prefs.daily_reminder_enabled = 'daily_reminder_enabled' in request.POST
        daily_time = request.POST.get('daily_reminder_time', '').strip()
        if daily_time:
            prefs.daily_reminder_time = daily_time
        prefs.weekly_summary_enabled = 'weekly_summary_enabled' in request.POST
        prefs.monthly_review_enabled = 'monthly_review_enabled' in request.POST
        prefs.email_notifications = 'email_notifications' in request.POST

        prefs.save()
        from accounts.translations import TRANSLATIONS
        msg = TRANSLATIONS.get(prefs.language, TRANSLATIONS['fr']).get('msg_prefs_saved', 'Vos préférences ont été enregistrées avec succès !')
        messages.success(request, msg)

        response = redirect('accounts:preferences')
        response.set_cookie('django_language', prefs.language, max_age=365*24*3600)
        return response


def set_language_view(request):
    """Allows instant language toggle via GET or POST."""
    lang = request.GET.get('lang') or request.POST.get('lang', 'fr')
    if lang not in ['fr', 'en']:
        lang = 'fr'

    if request.user.is_authenticated:
        try:
            prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
            prefs.language = lang
            prefs.save(update_fields=['language'])
        except Exception:
            pass

    request.session['django_language'] = lang
    from django.utils import translation
    translation.activate(lang)

    next_url = request.GET.get('next') or request.POST.get('next') or request.META.get('HTTP_REFERER') or '/journal/'
    from accounts.translations import TRANSLATIONS
    msg = TRANSLATIONS.get(lang, TRANSLATIONS['fr']).get('msg_lang_changed', 'Langue mise à jour.')
    messages.success(request, msg)

    response = redirect(next_url)
    response.set_cookie('django_language', lang, max_age=365*24*3600)
    return response


@method_decorator(login_required, name='dispatch')
class TemplatePasswordChangeView(View):
    """Direct route for password change."""
    def get(self, request):
        return redirect('/comptes/preferences/#securite')

    def post(self, request):
        from django.contrib.auth import update_session_auth_hash
        current_pwd = request.POST.get('current_password', '')
        new_pwd = request.POST.get('new_password', '')
        confirm_pwd = request.POST.get('confirm_password', '')

        if not request.user.check_password(current_pwd):
            messages.error(request, 'Le mot de passe actuel est incorrect.')
            return redirect('/comptes/preferences/#securite')
        if len(new_pwd) < 8:
            messages.error(request, 'Le nouveau mot de passe doit comporter au moins 8 caracteres.')
            return redirect('/comptes/preferences/#securite')
        if new_pwd != confirm_pwd:
            messages.error(request, 'Les deux nouveaux mots de passe ne correspondent pas.')
            return redirect('/comptes/preferences/#securite')

        request.user.set_password(new_pwd)
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Votre mot de passe a ete modifie avec succes !')
        return redirect('/comptes/preferences/#securite')


@login_required
def redirect_to_prefs_notifications(request):
    return redirect('/comptes/preferences/#notifications')


class TemplatePasswordResetView(View):
    """HTML password reset request page."""

    def get(self, request):
        return render(request, 'accounts/password_reset.html', {'form': None})

    def post(self, request):
        import secrets
        from datetime import timedelta
        from django.utils import timezone
        from .models import PasswordResetToken

        email = request.POST.get('email', '').strip()
        if email:
            try:
                user = User.objects.get(email=email)
                token = secrets.token_urlsafe(32)
                PasswordResetToken.objects.create(
                    user=user, token=token,
                    expires_at=timezone.now() + timedelta(hours=2),
                )
                logger.info(f'Password reset for {email}')
            except User.DoesNotExist:
                pass
        messages.success(request, 'Si ce compte existe, un email de reinitialisation a ete envoye.')
        return redirect('accounts:login')


@login_required
def template_delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.info(request, 'Votre compte a ete supprime.')
        return redirect('accounts:login')
    return redirect('accounts:profile')
