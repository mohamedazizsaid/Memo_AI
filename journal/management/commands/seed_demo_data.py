"""
MemoAi — Seed Demo Data Command
Creates a demo user with rich journal entries, tags, AI insights, and notifications.
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from accounts.models import User, UserPreferences
from journal.models import JournalEntry
from tags.models import Tag
from ai.models import AIAnalysis
from persons.models import Person, FaceDetection
from media_app.models import Media
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Populates the database with realistic demo journal entries and AI insights'

    def handle(self, *args, **options):
        self.stdout.write("Seeding MemoAi demo data...")

        # 1. Create or get demo user
        user, created = User.objects.get_or_create(
            email='demo@memoai.local',
            defaults={
                'first_name': 'Sophie',
                'last_name': 'Bernard',
            }
        )
        user.set_password('DemoPass123!')
        user.save()

        UserPreferences.objects.get_or_create(
            user=user,
            defaults={
                'theme': 'dark',
                'daily_reminder_enabled': True,
                'weekly_summary_enabled': True,
                'email_notifications': True,
                'face_recognition_consent': True,
            }
        )

        # 2. Create Tags
        tags_data = [
            {'name': 'Voyages', 'color': '#3b82f6', 'icon': '✈️'},
            {'name': 'Inspiration', 'color': '#8b5cf6', 'icon': '💡'},
            {'name': 'Nature', 'color': '#10b981', 'icon': '🌿'},
            {'name': 'Famille', 'color': '#ec4899', 'icon': '❤️'},
            {'name': 'Gratitude', 'color': '#f59e0b', 'icon': '🙏'},
        ]
        created_tags = {}
        for t in tags_data:
            tag, _ = Tag.objects.get_or_create(
                user=user,
                name=t['name'],
                defaults={'color': t['color'], 'icon': t['icon']}
            )
            created_tags[t['name']] = tag

        # 3. Create Persons
        lucas, _ = Person.objects.get_or_create(user=user, name='Lucas')
        emma, _ = Person.objects.get_or_create(user=user, name='Emma')

        today = date.today()

        # 4. Create Entries
        demo_entries = [
            {
                'title': 'Randonnée au lever du soleil sur les crêtes',
                'content': "Le réveil à 5h du matin en valait tellement la peine. L'air était vif et le brouillard dans la vallée s'est lentement dissipé sous les premiers rayons d'or. Nous avons partagé un thé chaud face aux sommets avec Lucas et Emma. Un moment suspendu, loin du bruit du monde, où chaque respiration semblait régénérer mon esprit.",
                'entry_date': today,
                'mood': 'amazing',
                'location': 'Chamonix-Mont-Blanc, France',
                'tags': ['Voyages', 'Nature', 'Gratitude'],
                'ai': {
                    'sentiment': 'positive',
                    'sentiment_score': 0.94,
                    'dominant_emotion': 'Émerveillement',
                    'keywords': ['lever du soleil', 'sommet', 'paix', 'nature', 'partage'],
                    'summary': "Une escapade matinale ressourçante en montagne, marquée par la sérénité du lever du soleil et la complicité partagée avec des proches.",
                    'generated_image_url': 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80',
                    'image_prompt': "A breathtaking mountain sunrise over misty alpine peaks with golden glow",
                },
                'image_url': 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80',
                'person': lucas,
            },
            {
                'title': 'Nouveau chapitre professionnel & réflexions',
                'content': "Dernière journée sur le projet qui m'a occupé pendant 6 mois. Beaucoup d'émotions mélangées : la satisfaction du travail accompli et la nostalgie de quitter cette équipe formidable. Ce soir, je ressens une paix profonde et une grande curiosité pour les défis qui m'attendent la semaine prochaine.",
                'entry_date': today - timedelta(days=2),
                'mood': 'grateful',
                'location': 'Paris, France',
                'tags': ['Inspiration', 'Gratitude'],
                'ai': {
                    'sentiment': 'positive',
                    'sentiment_score': 0.82,
                    'dominant_emotion': 'Reconnaissance',
                    'keywords': ['transition', 'projet', 'équipe', 'accomplissement', 'futur'],
                    'summary': "Clôture d'une étape professionnelle vécue avec fierté, introspection et enthousiasme pour l'avenir.",
                    'generated_image_url': 'https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=1200&q=80',
                    'image_prompt': "A cozy creative workspace desk bathed in soft warm afternoon sunlight",
                },
                'image_url': 'https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=800&q=80',
            },
            {
                'title': 'Après-midi pluvieux au café & lecture',
                'content': "Une averse torrentielle s'est abattue sur la ville. Réfugiée au coin d'un café avec un livre captivant et une tasse de chocolat chaud. Il y a une beauté particulière dans ces après-midis lents où l'on prend le temps de simplement observer la pluie couler sur les vitres.",
                'entry_date': today - timedelta(days=5),
                'mood': 'good',
                'location': 'Lyon, France',
                'tags': ['Inspiration', 'Nature'],
                'ai': {
                    'sentiment': 'positive',
                    'sentiment_score': 0.78,
                    'dominant_emotion': 'Sérénité',
                    'keywords': ['pluie', 'café', 'lecture', 'calme', 'chocolat'],
                    'summary': "Un moment de calme introspectif et chaleureux, savouré en observant la pluie à l'abri d'un café.",
                    'generated_image_url': 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=1200&q=80',
                    'image_prompt': "A peaceful aesthetic coffee shop window on a rainy autumn day",
                },
                'image_url': 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=800&q=80',
            },
            {
                'title': 'Doutes et fatigue passagère',
                'content': "Aujourd'hui a été une journée plus lourde que d'habitude. L'impression de courir après le temps et de ne pas avancer. J'ai eu du mal à me concentrer. Mais j'écris cela justement pour l'extérioriser : accepter les baisses d'énergie fait aussi partie du chemin.",
                'entry_date': today - timedelta(days=9),
                'mood': 'tired',
                'location': 'Maison',
                'tags': [],
                'ai': {
                    'sentiment': 'negative',
                    'sentiment_score': 0.35,
                    'dominant_emotion': 'Fatigue',
                    'keywords': ['fatigue', 'temps', 'pression', 'introspection', 'acceptation'],
                    'summary': "Journée marquée par une baisse d'énergie et une surcharge mentale, transformée en acceptation bienveillante par l'écriture.",
                },
            },
            {
                'title': 'Anniversaire surprise pour Emma !',
                'content': "Mission accomplie : elle ne se doutait de rien ! Quand elle a ouvert la porte et que tout le monde a crié, son regard valait tout l'or du monde. Rires jusqu'à minuit, vieux souvenirs d'enfance partagés, et ce gâteau aux framboises mémorable.",
                'entry_date': today - timedelta(days=14),
                'mood': 'excited',
                'location': 'Bordeaux, France',
                'tags': ['Famille', 'Gratitude'],
                'ai': {
                    'sentiment': 'positive',
                    'sentiment_score': 0.98,
                    'dominant_emotion': 'Joie intense',
                    'keywords': ['surprise', 'fête', 'rires', 'amitié', 'souvenirs'],
                    'summary': "Célébration chaleureuse et émouvante d'un anniversaire surprise réussi, empreint de complicité et de bonheur partagé.",
                    'generated_image_url': 'https://images.unsplash.com/photo-1513151233558-d860c5398176?auto=format&fit=crop&w=1200&q=80',
                    'image_prompt': "A warm aesthetic celebration with fairy lights and joy",
                },
                'image_url': 'https://images.unsplash.com/photo-1513151233558-d860c5398176?auto=format&fit=crop&w=800&q=80',
                'person': emma,
            },
        ]

        for item in demo_entries:
            entry, created = JournalEntry.objects.get_or_create(
                user=user,
                title=item['title'],
                defaults={
                    'content': item['content'],
                    'entry_date': item['entry_date'],
                    'mood': item['mood'],
                    'location': item.get('location', ''),
                    'ai_status': 'completed',
                }
            )

            # Assign tags
            if item.get('tags'):
                for t_name in item['tags']:
                    if t_name in created_tags:
                        entry.tags.add(created_tags[t_name])

            # Assign AI Analysis
            if 'ai' in item:
                ai_info = item['ai']
                AIAnalysis.objects.get_or_create(
                    entry=entry,
                    defaults={
                        'sentiment': ai_info.get('sentiment', 'neutral'),
                        'sentiment_score': ai_info.get('sentiment_score', 0.5),
                        'mood_insight': ai_info.get('dominant_emotion', ''),
                        'keywords': ai_info.get('keywords', []),
                        'summary': ai_info.get('summary', ''),
                        'generated_image_url': ai_info.get('generated_image_url', ''),
                        'summary_status': 'completed',
                        'sentiment_status': 'completed',
                        'image_generation_status': 'completed' if ai_info.get('generated_image_url') else 'skipped',
                    }
                )


            # Assign Media if provided
            if 'image_url' in item:
                media, _ = Media.objects.get_or_create(
                    entry=entry,
                    storage_url=item['image_url'],
                    defaults={
                        'media_type': 'IMAGE',
                        'file_size': 1024 * 350,
                        'mime_type': 'image/jpeg',
                    }
                )
                if 'person' in item:
                    FaceDetection.objects.get_or_create(
                        media=media,
                        person=item['person'],
                        defaults={
                            'confidence': 0.92,
                            'bounding_box': {'x': 100, 'y': 80, 'w': 120, 'h': 120},
                        }
                    )

        # 5. Create notifications
        Notification.objects.get_or_create(
            user=user,
            title="Bienvenue dans votre sanctuaire MemoAi ✨",
            defaults={
                'message': "Votre journal intime intelligent est prêt. Racontez vos journées, notez vos pensées vocales et laissez l'IA révéler vos émotions.",
                'notification_type': 'system',
                'is_read': True,
            }
        )

        Notification.objects.get_or_create(
            user=user,
            title="Flashback Nostalgie : Il y a 1 an 🍂",
            defaults={
                'message': "Redécouvrez votre souvenir « Randonnée au lever du soleil sur les crêtes » !",
                'notification_type': 'memory_nostalgia',
                'is_read': False,
            }
        )

        self.stdout.write(self.style.SUCCESS("Demo data successfully seeded for demo@memoai.local!"))
