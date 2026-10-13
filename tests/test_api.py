"""
MemoAi — Backend Integration Tests
Tests authentication, journal CRUD, tags, persons, notifications, and stats.
"""

import pytest
from datetime import date
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User
from journal.models import JournalEntry
from tags.models import Tag
from notifications.models import Notification
from persons.models import Person


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        email='testuser@memoai.local',
        password='TestPassword123!',
        first_name='Jean',
        last_name='Dupont',
    )
    return user


@pytest.fixture
def auth_client(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.mark.django_db
class TestAuthentication:
    def test_register_user(self, api_client):
        data = {
            'email': 'newuser@memoai.local',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
            'first_name': 'Alice',
            'last_name': 'Martin',
        }
        response = api_client.post('/api/auth/register/', data)
        assert response.status_code == 201
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert User.objects.filter(email='newuser@memoai.local').exists()

    def test_login_user(self, api_client, test_user):
        data = {
            'email': 'testuser@memoai.local',
            'password': 'TestPassword123!',
        }
        response = api_client.post('/api/auth/login/', data)
        assert response.status_code == 200
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']

    def test_get_current_user_profile(self, auth_client, test_user):
        response = auth_client.get('/api/auth/me/')
        assert response.status_code == 200
        assert response.data['email'] == test_user.email
        assert response.data['first_name'] == 'Jean'


@pytest.mark.django_db
class TestJournalAndTags:
    def test_create_and_list_tag(self, auth_client):
        # Create tag
        response = auth_client.post('/api/tags/', {
            'name': 'Voyage',
            'color': '#3b82f6',
            'icon': '✈️',
        })
        assert response.status_code == 201
        tag_id = response.data['id']

        # List tags
        list_resp = auth_client.get('/api/tags/')
        assert list_resp.status_code == 200
        assert len(list_resp.data) >= 1
        assert list_resp.data[0]['name'] == 'Voyage'

    def test_create_journal_entry_with_tag(self, auth_client, test_user):
        tag = Tag.objects.create(user=test_user, name='Bonheur', color='#10b981')

        entry_data = {
            'title': 'Une journée mémorable',
            'content': 'Aujourd\'hui était une magnifique journée ensoleillée passée dans la nature.',
            'entry_date': str(date.today()),
            'mood': 'amazing',
            'location': 'Paris, France',
            'tag_ids': [str(tag.id)],
        }
        response = auth_client.post('/api/entries/', entry_data)
        assert response.status_code == 201
        assert response.data['title'] == 'Une journée mémorable'
        assert response.data['mood'] == 'amazing'
        assert response.data['mood_emoji'] == '🤩'

        # Check list
        list_resp = auth_client.get('/api/entries/')
        assert list_resp.status_code == 200
        assert len(list_resp.data['results']) == 1

        # Check stats
        stats_resp = auth_client.get('/api/entries/stats/')
        assert stats_resp.status_code == 200
        assert stats_resp.data['total_entries'] == 1
        assert stats_resp.data['most_used_mood'] == 'amazing'


@pytest.mark.django_db
class TestNotifications:
    def test_notifications_flow(self, auth_client, test_user):
        # Create a notification
        notif = Notification.objects.create(
            user=test_user,
            title='Bienvenue sur MemoAi',
            message='Votre espace intime et sécurisé est prêt.',
            notification_type='system',
        )

        # List notifications
        list_resp = auth_client.get('/api/notifications/')
        assert list_resp.status_code == 200
        assert list_resp.data['unread_count'] == 1
        assert len(list_resp.data['results']) == 1

        # Mark as read
        read_resp = auth_client.post(f'/api/notifications/{notif.id}/read/')
        assert read_resp.status_code == 200
        assert read_resp.data['notification']['is_read'] is True

        # Mark all read
        mark_all = auth_client.post('/api/notifications/mark-all-read/')
        assert mark_all.status_code == 200


@pytest.mark.django_db
class TestPersons:
    def test_person_crud(self, auth_client, test_user):
        person = Person.objects.create(user=test_user, name='Sophie')
        response = auth_client.get(f'/api/people/{person.id}/')
        assert response.status_code == 200
        assert response.data['name'] == 'Sophie'

        # Update person name
        patch_resp = auth_client.patch(f'/api/people/{person.id}/', {'name': 'Sophie Laurent'})
        assert patch_resp.status_code == 200
        assert patch_resp.data['name'] == 'Sophie Laurent'
