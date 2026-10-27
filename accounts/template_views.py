"""
MemoAi — Accounts Template Views
HTML interface for authentication and profile management.
"""

import logging
from datetime import datetime

from django import forms
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from .models import UserPreferences

logger = logging.getLogger('memoai')
User = get_user_model()


def _upload_avatar(user, avatar_file):
    """Upload a profile photo to Cloudinary and return its secure URL."""
    from common.cloud_media import upload_avatar

    return upload_avatar(avatar_file, user.id, kind='avatars')


def _avatar_warning(request):
    is_en = str(getattr(request, 'LANGUAGE_CODE', 'fr')).lower().startswith('en')
    return ('Your photo could not be uploaded to Cloudinary. '
            'Your account is still saved without it.') if is_en else (
        "Votre photo n'a pas pu être envoyée vers Cloudinary. "
        "Votre compte est enregistré sans photo.")


def _with_welcome(target):
    """Append `?welcome=1` to a redirect target without breaking anchors.

    The intro splash (templates/partials/splash.html) is replayed whenever
    that flag is present, so every fresh sign-in gets the full entrance
    animation even if the visitor already browsed the platform.
    """
    path, _, fragment = target.partition('#')
    separator = '&' if '?' in path else '?'
    url = f'{path}{separator}welcome=1'
    return f'{url}#{fragment}' if fragment else url


def _needs_onboarding(user):
    try:
        return not user.preferences.onboarding_completed
    except Exception:
        return False


def _post_login_target(user):
    """Send staff users to the admin dashboard; others to journal (or onboarding)."""
    if user.is_staff:
        return '/admin-panel/'
    if _needs_onboarding(user):
        return reverse('accounts:onboarding')
    return reverse('journal:home')


def _safe_next(request):
    """Return a validated local ``next`` target, or an empty string."""
    target = request.POST.get('next') or request.GET.get('next') or ''
    if target and url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return ''


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
            return redirect(_post_login_target(request.user))
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
                # "Remember me" → 2-week persistent session; otherwise the
                # session cookie dies when the browser closes.
                from django.conf import settings as _settings
                if request.POST.get('remember_me'):
                    request.session.set_expiry(_settings.SESSION_COOKIE_AGE)
                else:
                    request.session.set_expiry(0)
                messages.success(request, f'Bienvenue, {user.first_name} !')
                if _needs_onboarding(user):
                    target = _safe_next(request)
                    return redirect(
                        f"{reverse('accounts:onboarding')}?next={target}" if target else 'accounts:onboarding'
                    )
                return redirect(_with_welcome(request.GET.get('next') or reverse('journal:home')))
            else:
                form.add_error(None, 'Email ou mot de passe incorrect.')
        return render(request, 'accounts/login.html', {'form': form})


class TemplateRegisterView(View):
    """HTML registration page."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(_post_login_target(request.user))
        return render(request, 'accounts/register.html', {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Handle avatar file upload — Cloudinary only, never local disk.
            avatar_file = request.FILES.get('avatar_file')
            if avatar_file:
                try:
                    user.avatar = _upload_avatar(user, avatar_file)
                    user.save(update_fields=['avatar'])
                except Exception as exc:
                    logger.warning('Cloudinary avatar upload failed: %s', exc)
                    messages.warning(request, _avatar_warning(request))
            elif request.POST.get('avatar_url'):
                user.avatar = request.POST.get('avatar_url').strip()
                user.save(update_fields=['avatar'])

            # Capture initial theme preference from registration state
            theme = request.POST.get('theme', '').strip()
            if theme in dict(UserPreferences.THEME_CHOICES):
                prefs, _ = UserPreferences.objects.get_or_create(user=user)
                prefs.theme = theme
                prefs.save(update_fields=['theme'])

            login(request, user)
            messages.success(request, f'Compte cree avec succes ! Bienvenue, {user.first_name} !')
            # New accounts always meet the animated onboarding first.
            return redirect('accounts:onboarding')
        return render(request, 'accounts/register.html', {'form': form})


@method_decorator(login_required, name='dispatch')
class TemplateOnboardingView(View):
    """Animated, multi-step welcome flow shown once right after registration."""

    template_name = 'accounts/onboarding.html'

    def get(self, request):
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        replay = request.GET.get('replay') == '1'
        if prefs.onboarding_completed and not replay:
            return redirect('journal:home')
        return render(request, self.template_name, {
            'preferences': prefs,
            'onboarding_mode': True,
            'replay': replay,
            'next_url': _safe_next(request),
        })

    def post(self, request):
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)

        if request.POST.get('skip') == '1':
            theme = request.POST.get('theme', '').strip()
            if theme in dict(UserPreferences.THEME_CHOICES):
                prefs.theme = theme
            lang = request.POST.get('language', '').strip()
            if lang in dict(UserPreferences.LANGUAGE_CHOICES):
                prefs.language = lang
                request.session['django_language'] = lang
            prefs.onboarding_completed = True
            prefs.onboarding_completed_at = timezone.now()
            prefs.save()
            messages.info(request, 'Vous pourrez modifier ces choix dans vos préférences.'
                          if not str(getattr(request, 'LANGUAGE_CODE', 'fr')).startswith('en')
                          else 'You can change these choices anytime in your preferences.')
            return redirect(_with_welcome(reverse('journal:home')))

        gender = request.POST.get('gender', '').strip()
        if gender in dict(UserPreferences.GENDER_CHOICES):
            prefs.gender = gender

        visibility = request.POST.get('profile_visibility', '').strip()
        if visibility in dict(UserPreferences.PROFILE_VISIBILITY_CHOICES):
            prefs.profile_visibility = visibility

        theme = request.POST.get('theme', '').strip()
        if theme in dict(UserPreferences.THEME_CHOICES):
            prefs.theme = theme

        lang = request.POST.get('language', '').strip()
        if lang in dict(UserPreferences.LANGUAGE_CHOICES):
            prefs.language = lang
            request.session['django_language'] = lang

        prefs.reduce_motion = 'reduce_motion' in request.POST
        prefs.daily_reminder_enabled = 'daily_reminder_enabled' in request.POST

        daily_time = request.POST.get('daily_reminder_time', '').strip()
        if daily_time:
            try:
                prefs.daily_reminder_time = datetime.strptime(daily_time, '%H:%M').time()
            except ValueError:
                pass

        prefs.onboarding_completed = True
        prefs.onboarding_completed_at = timezone.now()
        prefs.save()

        target = _safe_next(request)
        messages.success(
            request,
            'Tout est prêt — bienvenue dans votre journal intelligent !'
            if prefs.language != 'en' else
            'All set — welcome to your intelligent journal!',
        )

        response = redirect(target) if target else redirect(_with_welcome(reverse('journal:home')))
        response.set_cookie('django_language', prefs.language, max_age=365 * 24 * 3600)
        return response


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
            try:
                user.avatar = _upload_avatar(user, avatar_file)
            except Exception as exc:
                logger.warning('Cloudinary avatar upload failed: %s', exc)
                messages.warning(request, _avatar_warning(request))
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

        # Identity & privacy (also chosen during onboarding)
        gender = request.POST.get('gender', '').strip()
        if gender in dict(UserPreferences.GENDER_CHOICES):
            prefs.gender = gender
        visibility = request.POST.get('profile_visibility', '').strip()
        if visibility in dict(UserPreferences.PROFILE_VISIBILITY_CHOICES):
            prefs.profile_visibility = visibility

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


def _email_text(request, lang, key):
    """Small bilingual dictionary for the password-reset email."""
    table = {
        'fr': {
            'subject': 'Réinitialisez votre mot de passe MemoAI',
            'title': 'Réinitialiser votre mot de passe',
            'hello': 'Bonjour',
            'intro': "Vous avez demandé à réinitialiser le mot de passe de votre compte MemoAI.",
            'cta': 'Choisir un nouveau mot de passe',
            'expiry': 'Ce lien est valable pendant 2 heures.',
            'ignore': "Si vous n'êtes pas à l'origine de cette demande, ignorez simplement cet email.",
            'fallback': "Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :",
        },
        'en': {
            'subject': 'Reset your MemoAI password',
            'title': 'Reset your password',
            'hello': 'Hello',
            'intro': 'You requested to reset the password of your MemoAI account.',
            'cta': 'Choose a new password',
            'expiry': 'This link is valid for 2 hours.',
            'ignore': "If you didn't request this, you can safely ignore this email.",
            'fallback': "If the button doesn't work, copy this link into your browser:",
        },
    }
    lang = lang if lang in table else 'fr'
    return table[lang].get(key, '')


def _send_password_reset_email(request, user, token):
    """Render and send the bilingual password-reset email."""
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.urls import reverse

    try:
        lang = 'fr'
        try:
            lang = user.preferences.language
        except Exception:
            pass

        path = reverse('accounts:password-reset-confirm', kwargs={'token': token})
        reset_url = request.build_absolute_uri(path)
        keys = ['title', 'hello', 'intro', 'cta', 'expiry', 'ignore', 'fallback']
        ctx = {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'MemoAI',
            'lang': lang,
            'strings': {k: _email_text(request, lang, k) for k in keys},
        }
        subject = _email_text(request, lang, 'subject')
        text_body = render_to_string('accounts/emails/password_reset_email.txt', ctx)
        html_body = render_to_string('accounts/emails/password_reset_email.html', ctx)
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'MemoAi <noreply@memoai.app>')
        msg = EmailMultiAlternatives(subject, text_body, from_email, [user.email])
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        logger.info('Password reset email sent to %s', user.email)
        return True
    except Exception as exc:  # pragma: no cover - depends on SMTP config
        logger.error('Password reset email failed for %s: %s', user.email, exc)
        return False


class TemplatePasswordResetView(View):
    """HTML password reset request page."""

    def get(self, request):
        return render(request, 'accounts/password_reset.html', {'form': None, 'sent': False})

    def post(self, request):
        import secrets
        from datetime import timedelta
        from django.utils import timezone
        from .models import PasswordResetToken

        email = request.POST.get('email', '').strip()
        sent = False
        if email:
            try:
                user = User.objects.get(email=email)
                # Invalidate previous unused tokens for this user.
                PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
                token = secrets.token_urlsafe(32)
                PasswordResetToken.objects.create(
                    user=user, token=token,
                    expires_at=timezone.now() + timedelta(hours=2),
                )
                sent = _send_password_reset_email(request, user, token)
            except User.DoesNotExist:
                pass
        # Never reveal whether the account exists.
        return render(request, 'accounts/password_reset.html', {
            'form': None,
            'sent': True,
            'email': email,
        })


class TemplatePasswordResetConfirmView(View):
    """Set a new password from a reset token."""

    def _get_token(self, token):
        from .models import PasswordResetToken
        try:
            obj = PasswordResetToken.objects.select_related('user').get(token=token)
        except PasswordResetToken.DoesNotExist:
            return None
        return obj if obj.is_valid else None

    def get(self, request, token):
        reset = self._get_token(token)
        return render(request, 'accounts/password_reset_confirm.html', {
            'token': token,
            'valid': reset is not None,
        })

    def post(self, request, token):
        reset = self._get_token(token)
        if reset is None:
            return render(request, 'accounts/password_reset_confirm.html', {
                'token': token,
                'valid': False,
            })

        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if len(password1) < 8:
            return render(request, 'accounts/password_reset_confirm.html', {
                'token': token, 'valid': True,
                'error': 'Le mot de passe doit comporter au moins 8 caracteres.',
            })
        if password1 != password2:
            return render(request, 'accounts/password_reset_confirm.html', {
                'token': token, 'valid': True,
                'error': 'Les deux mots de passe ne correspondent pas.',
            })

        user = reset.user
        user.set_password(password1)
        user.save(update_fields=['password'])
        reset.used = True
        reset.save(update_fields=['used'])

        messages.success(request, 'Votre mot de passe a ete reinitialise. Vous pouvez maintenant vous connecter.')
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
