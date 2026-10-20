"""Seed a complete, local-only demo account for MemoAI.

The command is intentionally idempotent: it removes the demo user's journal
content (entries, media, AI analyses, tags, people, notifications and reset
tokens) and recreates a coherent story with local static images. Local assets
keep the cinematic reel exporter CORS-safe and make the demo work offline.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --email demo@memoai.local --password DemoPass123!
"""

from datetime import datetime, time, timedelta
import math
from pathlib import Path
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.templatetags.static import static
from django.utils import timezone

from accounts.models import PasswordResetToken, User, UserPreferences
from ai.models import AIAnalysis
from journal.models import JournalEntry
from media_app.models import Media
from notifications.models import Notification
from persons.models import FaceDetection, Person
from tags.models import EntryTag, Tag


TAG_SPECS = [
    {"name": "quotidien", "color": "#C8963E", "icon": "coffee"},
    {"name": "nature", "color": "#6B8F71", "icon": "leaf"},
    {"name": "amis", "color": "#D9776A", "icon": "users"},
    {"name": "voyage", "color": "#5B7FA6", "icon": "map-pin"},
    {"name": "famille", "color": "#B08968", "icon": "home"},
    {"name": "gourmand", "color": "#D9A441", "icon": "cake"},
    {"name": "travail", "color": "#7A7F87", "icon": "briefcase"},
    {"name": "automne", "color": "#A97142", "icon": "leaf"},
    {"name": "souvenirs", "color": "#8C6A9E", "icon": "clock"},
    {"name": "creativite", "color": "#4F8A8B", "icon": "pen"},
]

PERSON_SPECS = [
    {
        "key": "camille",
        "name": "Camille Laurent",
        "avatar": "img/tile_friends.jpg",
        "notes": "Amie d'enfance, retrouvée à Lyon autour d'un café.",
        "confirmed": True,
        "days_ago": 8,
    },
    {
        "key": "thomas",
        "name": "Thomas Moreau",
        "avatar": "img/tile_city.jpg",
        "notes": "Mon frère, photographe du dimanche et complice de toujours.",
        "confirmed": True,
        "days_ago": 19,
    },
    {
        "key": "lea",
        "name": "Léa Bernard",
        "avatar": "img/tile_sunset.jpg",
        "notes": "Collègue devenue amie autour des sorties running du jeudi.",
        "confirmed": True,
        "days_ago": 27,
    },
    {
        "key": "mamie",
        "name": "Mamie Jeanne",
        "avatar": "img/tile_coffee.jpg",
        "notes": "Les madeleines du dimanche et les histoires qui commencent par « quand j'étais petite ».",
        "confirmed": True,
        "days_ago": 65,
    },
    {
        "key": "hugo",
        "name": "Hugo Petit",
        "avatar": "img/orbit/o27.jpg",
        "notes": "Rencontré lors d'un atelier photo au canal.",
        "confirmed": False,
        "days_ago": 120,
    },
]


ENTRY_SPECS = [
    {
        "key": "cafe",
        "offset": 0,
        "title": "Le premier café de l'automne",
        "content": (
            "Ce matin, la lumière avait cette couleur dorée qui annonce l'automne. "
            "Je me suis installé à la terrasse du café des Deux Moulins avec un carnet "
            "et un flat white. Les feuilles commencent à peine à tomber, mais l'air a "
            "déjà ce parfum de rentrée. J'ai écrit trois idées sans les juger, juste "
            "pour retrouver le plaisir de poser les mots. En repartant, je me suis dit "
            "que cette saison serait celle des petites habitudes douces."
        ),
        "mood": "good",
        "location": "Café des Deux Moulins, Paris",
        "latitude": "48.886000",
        "longitude": "2.338000",
        "media": [(1, "IMAGE"), (2, "IMAGE")],
        "tags": ["quotidien", "gourmand", "automne"],
        "ai_tags": ["automne"],
        "sentiment": "positive",
        "score": 0.91,
        "summary": (
            "Une matinée simple et lumineuse, consacrée à l'écriture et au retour "
            "des rituels d'automne."
        ),
        "keywords": ["automne", "café", "lumière", "calme", "routine"],
        "insight": (
            "Les petits rituels et la lumière douce semblent poser un cadre rassurant "
            "pour écrire sans pression."
        ),
        "prompt": "Un café parisien baigné de lumière dorée d'automne, carnet ouvert sur la table.",
    },
    {
        "key": "parc",
        "offset": 1,
        "title": "Balade au parc avant la pluie",
        "content": (
            "Le ciel était bas et le parc presque vide. J'ai marché sans musique, en "
            "écoutant les feuilles et les quelques oiseaux qui résistaient au froid. "
            "Les fleurs du parterre avaient encore des couleurs incroyables. Juste avant "
            "que la pluie arrive, j'ai trouvé un banc et j'ai regardé les nuages glisser "
            "sur les toits. C'était une de ces heures où l'on ne fait rien et où tout "
            "semble pourtant se remettre en place."
        ),
        "mood": "amazing",
        "location": "Parc Monceau, Paris",
        "latitude": "48.879000",
        "longitude": "2.309000",
        "media": [(3, "IMAGE"), (4, "IMAGE")],
        "tags": ["nature", "quotidien"],
        "ai_tags": [],
        "sentiment": "positive",
        "score": 0.84,
        "summary": (
            "Une marche silencieuse avant la pluie, propice à l'observation et au "
            "ralentissement."
        ),
        "keywords": ["parc", "marche", "nature", "pluie", "respiration"],
        "insight": (
            "Le contact avec la nature et le silence semblent avoir apaisé le rythme "
            "mental de la journée."
        ),
        "prompt": "Un parc parisien sous un ciel de pluie, fleurs colorées et banc vide.",
    },
    {
        "key": "soiree",
        "offset": 2,
        "title": "Une soirée qui rallume les étoiles",
        "content": (
            "Camille et Thomas sont arrivés avec des vinyles et une tarte aux pommes. "
            "On a cuisiné, ri de nos vieilles photos et dansé dans le salon jusqu'à ce "
            "que les voisins demandent gentiment de baisser le volume. Léa nous a rejoints "
            "après son cours de danse. À minuit, on est montés sur la terrasse : le ciel "
            "était dégagé et la ville entière semblait respirer. J'avais oublié à quel "
            "point une soirée simple pouvait recharger autant."
        ),
        "mood": "excited",
        "location": "Belleville, Paris",
        "latitude": "48.872000",
        "longitude": "2.381000",
        "media": [(5, "IMAGE"), (6, "IMAGE")],
        "tags": ["amis", "creativite", "quotidien"],
        "ai_tags": ["amis"],
        "sentiment": "positive",
        "score": 0.93,
        "summary": (
            "Une soirée entre amis faite de musique, de cuisine et de rires, qui a "
            "redonné de l'énergie."
        ),
        "keywords": ["amis", "musique", "rires", "soirée", "étoiles"],
        "insight": (
            "La présence des proches et la créativité partagée sont clairement des "
            "sources de joie et de reconnexion."
        ),
        "prompt": "Une terrasse parisienne la nuit, guirlandes lumineuses et amis qui rient.",
    },
    {
        "key": "dimanche",
        "offset": 4,
        "title": "Dimanche slow",
        "content": (
            "Pas de réveil, pas de liste. J'ai fait du café, lu deux chapitres et laissé "
            "la journée s'installer sans plan. Le carnet est resté ouvert sur la table "
            "sans que j'écrive vraiment. Parfois, le repos consiste simplement à ne pas "
            "remplir le vide. En fin d'après-midi, j'ai quand même noté une idée pour "
            "la semaine. Une petite idée, pas une mission."
        ),
        "mood": "neutral",
        "location": "Maison",
        "media": [(7, "IMAGE"), (8, "IMAGE")],
        "tags": ["quotidien", "creativite"],
        "ai_tags": [],
        "sentiment": "neutral",
        "score": 0.56,
        "summary": (
            "Une journée volontairement sans structure, partagée entre lecture, café "
            "et repos."
        ),
        "keywords": ["dimanche", "lecture", "calme", "maison", "ralentir"],
        "insight": (
            "Le besoin de ralentir est clair, même si le silence laisse aussi remonter "
            "quelques pensées en suspens."
        ),
        "prompt": "Un dimanche matin calme, tasse de café et livre ouvert près de la fenêtre.",
    },
    {
        "key": "dossier",
        "offset": 10,
        "title": "Le dossier qui n'en finit pas",
        "content": (
            "La journée a été longue. Le dossier avance, mais chaque relecture ouvre "
            "trois nouvelles questions. J'ai mangé devant l'écran et je le regrette un "
            "peu. En sortant, j'ai fait le tour du pâté de maisons pour décrocher. "
            "Le soir, j'ai fermé l'ordinateur sans répondre aux derniers messages. "
            "Demain, je demanderai de l'aide au lieu de vouloir tout porter seule."
        ),
        "mood": "stressed",
        "location": "Bureau",
        "media": [(9, "IMAGE"), (10, "IMAGE")],
        "tags": ["travail", "quotidien"],
        "ai_tags": ["travail"],
        "sentiment": "negative",
        "score": 0.21,
        "summary": (
            "Une journée de travail dense et frustrante, marquée par la pression et "
            "la difficulté à déconnecter."
        ),
        "keywords": ["travail", "pression", "fatigue", "délais", "bureau"],
        "insight": (
            "La charge mentale déborde sur les temps de pause. Poser une limite et "
            "demander de l'aide pourrait alléger la prochaine journée."
        ),
        "prompt": "Un bureau en fin de journée, écran allumé et ville grise derrière la fenêtre.",
    },
    {
        "key": "retrouvailles",
        "offset": 22,
        "title": "Retrouvailles avec Camille",
        "content": (
            "Cela faisait presque deux ans. On s'est retrouvées à Lyon, dans un petit "
            "café près des quais. Les premières minutes étaient timides, puis tout est "
            "revenu : nos blagues, nos silences et cette façon de finir les phrases de "
            "l'autre. On a parlé de nos vies sans comparaison, juste pour se raconter. "
            "En repartant, j'ai senti une chaleur tranquille. Certaines amitiés ne "
            "demandent qu'une table et un après-midi."
        ),
        "mood": "grateful",
        "location": "Lyon",
        "latitude": "45.764000",
        "longitude": "4.835700",
        "media": [(11, "IMAGE"), (12, "IMAGE")],
        "tags": ["amis", "souvenirs"],
        "ai_tags": ["amis"],
        "sentiment": "positive",
        "score": 0.97,
        "summary": (
            "Des retrouvailles émouvantes avec une amie d'enfance, vécues dans la "
            "simplicité et la gratitude."
        ),
        "keywords": ["retrouvailles", "amitié", "lyon", "souvenirs", "joie"],
        "insight": (
            "La reconnexion à une amitié ancienne procure un profond sentiment de "
            "continuité et de sécurité affective."
        ),
        "prompt": "Deux amies attablées dans un café lyonnais, lumière douce de fin d'après-midi.",
    },
    {
        "key": "ete",
        "offset": 36,
        "title": "Lumière de fin d'été",
        "content": (
            "Biarritz, dernier soir avant de rentrer. La plage était presque vide et "
            "l'océan avait cette couleur d'ardoise. J'ai marché jusqu'à la jetée en "
            "laissant le sable entrer dans mes chaussures. Le soleil descendait derrière "
            "les nuages, puis il a trouvé une fente et tout est devenu orange. Je n'ai "
            "pas pris trente photos. J'en ai pris une, puis je me suis assise. C'était "
            "exactement ce dont j'avais besoin."
        ),
        "mood": "good",
        "location": "Biarritz",
        "latitude": "43.483200",
        "longitude": "-1.558600",
        "media": [(13, "IMAGE"), (14, "IMAGE")],
        "tags": ["voyage", "nature"],
        "ai_tags": ["voyage"],
        "sentiment": "positive",
        "score": 0.88,
        "summary": (
            "Un dernier soir à Biarritz, entre océan, lumière et envie de ralentir."
        ),
        "keywords": ["été", "océan", "lumière", "voyage", "coucher de soleil"],
        "insight": (
            "La contemplation et la simplicité du paysage ont créé un moment de "
            "présence et de gratitude."
        ),
        "prompt": "Un coucher de soleil orangé sur l'océan à Biarritz, plage presque déserte.",
    },
    {
        "key": "route",
        "offset": 57,
        "title": "Sur la route des vacances",
        "content": (
            "On est partis tôt, avec une playlist trop longue et des sandwiches préparés "
            "la veille. La route traversait des champs de lavande et des villages de "
            "pierre. À chaque pause, on découvrait une nouvelle lumière. Thomas voulait "
            "photographier tous les panneaux, Léa voulait goûter tous les marchés. Moi, "
            "je conduisais et je souriais. La destination importait moins que cette "
            "sensation de temps ouvert devant nous."
        ),
        "mood": "excited",
        "location": "Provence",
        "latitude": "43.837400",
        "longitude": "5.040000",
        "media": [(15, "IMAGE"), (16, "GENERATED_IMAGE")],
        "tags": ["voyage", "nature", "amis"],
        "ai_tags": ["voyage"],
        "sentiment": "positive",
        "score": 0.92,
        "summary": (
            "Un road trip joyeux vers la Provence, rempli de paysages, de musique et "
            "de découvertes partagées."
        ),
        "keywords": ["route", "vacances", "provence", "paysage", "liberté"],
        "insight": (
            "Le voyage et l'imprévu nourrissent un sentiment de liberté et de complicité."
        ),
        "prompt": "Une route de Provence au milieu des champs de lavande, voiture au loin.",
    },
    {
        "key": "madeleines",
        "offset": 94,
        "title": "Le goût des madeleines",
        "content": (
            "Mamie Jeanne avait sorti le grand plat et la recette écrite à la main. "
            "On a pesé la farine, cassé les œufs et attendu devant le four en parlant "
            "de ses étés à la mer. La cuisine sentait le citron et le beurre. À la "
            "première bouchée, je suis retournée dans la cuisine de mon enfance. Elle "
            "a ri de me voir fermer les yeux. On a tout mangé sauf trois, soigneusement "
            "rangés pour demain."
        ),
        "mood": "grateful",
        "location": "Chez Mamie",
        "media": [(17, "IMAGE"), (18, "IMAGE")],
        "tags": ["famille", "gourmand", "souvenirs"],
        "ai_tags": ["famille"],
        "sentiment": "positive",
        "score": 0.86,
        "summary": (
            "Un après-midi de cuisine avec Mamie Jeanne, entre transmission, goûts "
            "d'enfance et tendresse."
        ),
        "keywords": ["madeleines", "famille", "enfance", "cuisine", "tendresse"],
        "insight": (
            "La cuisine partagée agit comme un pont entre les générations et ravive "
            "des souvenirs sensoriels heureux."
        ),
        "prompt": "Une cuisine familiale chaleureuse, madeleines dorées et recette écrite à la main.",
    },
    {
        "key": "noel",
        "offset": 300,
        "title": "Noël en petit comité",
        "content": (
            "Cette année, pas de grande tablée. Juste nous, une table plus petite et "
            "la cheminée allumée. On a cuisiné à plusieurs, mis de la musique douce et "
            "sorti les vieilles décorations. Thomas a offert un album photo qu'il avait "
            "fait en secret. Mamie a raconté une histoire que personne n'avait entendue. "
            "Le lendemain matin, les papiers cadeaux traînaient encore et la maison "
            "sentait le sapin. C'était un Noël calme, et c'était parfait."
        ),
        "mood": "good",
        "location": "Maison",
        "media": [(19, "IMAGE"), (20, "IMAGE")],
        "tags": ["famille", "souvenirs", "gourmand"],
        "ai_tags": [],
        "sentiment": "positive",
        "score": 0.79,
        "summary": (
            "Un Noël intime et chaleureux, centré sur la famille, les traditions et "
            "les attentions simples."
        ),
        "keywords": ["noël", "famille", "maison", "tradition", "chaleur"],
        "insight": (
            "La sobriété et l'intimité de cette fête semblent avoir renforcé le "
            "sentiment d'appartenance et de présence."
        ),
        "prompt": "Un salon décoré pour Noël, cheminée et table familiale, ambiance chaleureuse.",
    },
    {
        "key": "un_an",
        "years_ago": 1,
        "title": "Il y a un an, déjà",
        "content": (
            "Une année a passé. Je suis passée devant le café où j'avais l'habitude de "
            "travailler et j'ai commandé le même thé. Rien n'avait vraiment changé, et "
            "pourtant tout avait bougé. J'ai relu quelques pages de mon carnet de "
            "l'époque. J'avais peur de ne pas y arriver, peur de choisir la mauvaise "
            "direction. Aujourd'hui, je ne regrette pas le chemin. J'ai simplement envie "
            "de dire à la personne d'alors qu'elle a bien fait de continuer."
        ),
        "mood": "neutral",
        "location": "Paris",
        "media": [(21, "IMAGE")],
        "tags": ["souvenirs", "automne"],
        "ai_tags": ["souvenirs"],
        "sentiment": "neutral",
        "score": 0.57,
        "summary": (
            "Un bilan un an plus tard, entre reconnaissance du chemin parcouru et "
            "douce mélancolie."
        ),
        "keywords": ["souvenirs", "temps", "automne", "bilan", "douceur"],
        "insight": (
            "Le regard rétrospectif est apaisé : les inquiétudes de l'époque sont "
            "reconnues sans envahir le présent."
        ),
        "prompt": "Un café parisien en automne, carnet ouvert et thé fumant près de la vitre.",
    },
    {
        "key": "lettre",
        "years_ago": 2,
        "title": "La lettre retrouvée",
        "content": (
            "En rangeant un tiroir, j'ai trouvé une lettre que je n'avais jamais envoyée. "
            "Elle était pliée en quatre, avec une date et beaucoup d'hésitations. J'ai "
            "mis longtemps avant de l'ouvrir. La personne qui écrivait avait besoin de "
            "dire les choses sans lendemain. Je n'ai pas eu envie de la juger. Je l'ai "
            "lue deux fois, puis je l'ai rangée dans un carnet, pas pour l'oublier, juste "
            "pour la garder. Certaines paroles attendent simplement le bon moment pour "
            "être comprises."
        ),
        "mood": "grateful",
        "location": "Jardin du Luxembourg, Paris",
        "media": [(22, "IMAGE"), (23, "GENERATED_IMAGE")],
        "tags": ["souvenirs", "famille"],
        "ai_tags": ["souvenirs"],
        "sentiment": "positive",
        "score": 0.9,
        "summary": (
            "La découverte d'une lettre ancienne déclenche un retour apaisé sur les "
            "émotions du passé."
        ),
        "keywords": ["lettre", "souvenirs", "passé", "compréhension", "jardin"],
        "insight": (
            "La relecture du passé permet de transformer une blessure en objet de "
            "compassion, sans la nier."
        ),
        "prompt": "Une lettre ancienne dans un carnet, posée sur un banc de jardin baigné de lumière.",
    },
    {
        "key": "canal",
        "offset": 171,
        "title": "Carnet de bord au canal",
        "content": (
            "J'ai passé l'après-midi au canal avec mon appareil photo. Thomas m'avait "
            "prêté un objectif et j'ai tenté de regarder la ville autrement. Les gens "
            "assis sur les quais, les reflets, les vélos qui passent trop vite. Rien "
            "d'extraordinaire, et pourtant tout devenait une image possible. On a fini "
            "avec un verre sur une terrasse. Je crois que la créativité a aussi besoin "
            "de ces heures sans but précis."
        ),
        "mood": "good",
        "location": "Canal Saint-Martin, Paris",
        "media": [(24, "IMAGE"), (25, "IMAGE")],
        "tags": ["amis", "creativite", "quotidien"],
        "ai_tags": ["creativite"],
        "sentiment": "positive",
        "score": 0.74,
        "summary": (
            "Un après-midi de photographie au canal, où l'ordinaire devient matière "
            "à créativité."
        ),
        "keywords": ["dimanche", "photos", "amitié", "promenade", "créativité"],
        "insight": (
            "Le regard photographique aide à habiter le quotidien avec plus de curiosité "
            "et de légèreté."
        ),
        "prompt": "Le canal Saint-Martin à Paris, reflets dorés et silhouettes sur les quais.",
    },
]

FACE_SPECS = [
    {"person": "camille", "entry": "soiree", "media": 0, "confidence": 0.96, "box": [0.16, 0.58, 0.74, 0.34]},
    {"person": "thomas", "entry": "soiree", "media": 0, "confidence": 0.94, "box": [0.18, 0.82, 0.79, 0.57]},
    {"person": "lea", "entry": "soiree", "media": 0, "confidence": 0.92, "box": [0.42, 0.72, 0.84, 0.48]},
    {"person": "camille", "entry": "retrouvailles", "media": 0, "confidence": 0.95, "box": [0.12, 0.55, 0.76, 0.31]},
    {"person": "mamie", "entry": "madeleines", "media": 0, "confidence": 0.91, "box": [0.22, 0.61, 0.81, 0.37]},
    {"person": "thomas", "entry": "canal", "media": 0, "confidence": 0.89, "box": [0.24, 0.65, 0.78, 0.41]},
    {"person": "hugo", "entry": "lettre", "media": 1, "confidence": 0.87, "box": [0.30, 0.69, 0.73, 0.45], "corrected": True},
]


def _entry_date(today, spec):
    """Resolve a history date relative to the day the command is run."""
    if spec.get("years_ago"):
        target = today.replace(year=today.year - spec["years_ago"])
        # 29 February in a non-leap year: fall back to the last day of the month.
        if target.month != today.month:
            target = target.replace(month=2, day=28)
        return target
    return today - timedelta(days=spec["offset"])


def _aware_midmorning(day):
    return timezone.make_aware(datetime.combine(day, time(9, 0)))


def _orbit_url(index):
    return static(f"img/orbit/o{index:02d}.jpg")


def _orbit_size(index):
    path = Path(settings.BASE_DIR) / "static" / "img" / "orbit" / f"o{index:02d}.jpg"
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _embedding(seed):
    """Deterministic 128-float embedding so the people UI behaves like real data."""
    values = [0.5 + 0.5 * math.sin(seed * 1.7 + i * 0.41) for i in range(128)]
    return ",".join(f"{value:.5f}" for value in values)


def _clear_demo_content(user):
    # Queryset.delete() permanently removes rows; JournalEntry inherits soft
    # delete but this reset is explicitly meant to rebuild the demo from zero.
    JournalEntry.all_objects.filter(user=user).delete()
    Person.objects.filter(user=user).delete()
    Tag.objects.filter(user=user).delete()
    Notification.objects.filter(user=user).delete()
    PasswordResetToken.objects.filter(user=user).delete()


def _create_media(entry, index, media_type):
    url = _orbit_url(index)
    return Media.objects.create(
        entry=entry,
        media_type=media_type,
        storage_url=url,
        mime_type="image/jpeg",
        file_size=_orbit_size(index),
        width=1200,
        height=1600,
        original_filename=Path(url).name,
        processing_status="completed",
    )


def _create_analysis(entry, spec, media_list):
    generated_url = next(
        (item.storage_url for item in media_list if item.media_type == "GENERATED_IMAGE"),
        "",
    )
    return AIAnalysis.objects.create(
        entry=entry,
        transcription="",
        transcription_language="",
        transcription_status="skipped",
        summary=spec["summary"],
        keywords=spec["keywords"],
        mood_insight=spec["insight"],
        summary_status="completed",
        sentiment=spec["sentiment"],
        sentiment_score=spec["score"],
        sentiment_status="completed",
        generated_image_url=generated_url,
        image_prompt=spec["prompt"],
        image_generation_status="completed" if generated_url else "skipped",
    )


def _seed_notifications(user, entries_by_key):
    now = timezone.now()
    coffee = entries_by_key["cafe"]
    soiree = entries_by_key["soiree"]
    un_an = entries_by_key["un_an"]
    notifications = [
        {
            "title": "Votre analyse IA est prête",
            "message": "Le résumé, le sentiment et les mots-clés de « Le premier café de l'automne » sont disponibles.",
            "notification_type": "ai_complete",
            "hours_ago": 1,
            "is_read": False,
            "data": {"entry_id": str(coffee.id), "url": f"/journal/{coffee.id}/"},
        },
        {
            "title": "Un souvenir vous attend",
            "message": "Il y a un an, vous écriviez « Il y a un an, déjà ». Envie de le relire ?",
            "notification_type": "memory_nostalgia",
            "hours_ago": 3,
            "is_read": False,
            "data": {"entry_id": str(un_an.id), "url": f"/journal/{un_an.id}/"},
        },
        {
            "title": "Votre résumé hebdomadaire",
            "message": "Trois entrées, deux nouvelles photos et une humeur dominante : votre semaine en un regard.",
            "notification_type": "weekly_summary",
            "hours_ago": 20,
            "is_read": False,
            "data": {"url": "/insights/"},
        },
        {
            "title": "Petit rappel du jour",
            "message": "Prenez cinq minutes pour noter ce qui vous a marqué aujourd'hui.",
            "notification_type": "daily_reminder",
            "hours_ago": 26,
            "is_read": True,
            "data": {"url": "/journal/nouveau/"},
        },
        {
            "title": "Série de 3 jours",
            "message": "Vous avez écrit chaque jour depuis trois jours. Continuez sur cette lancée.",
            "notification_type": "streak_milestone",
            "hours_ago": 46,
            "is_read": False,
            "data": {"url": "/journal/"},
        },
        {
            "title": "Votre rétrospective mensuelle",
            "message": "Le mois dernier, vos souvenirs ont surtout tourné autour de la famille et des voyages.",
            "notification_type": "monthly_review",
            "hours_ago": 120,
            "is_read": True,
            "data": {"url": "/insights/?period=90"},
        },
        {
            "title": "Analyse terminée",
            "message": "La soirée à Belleville a été analysée : une entrée pleine d'énergie et d'amitié.",
            "notification_type": "ai_complete",
            "hours_ago": 72,
            "is_read": True,
            "data": {"entry_id": str(soiree.id), "url": f"/journal/{soiree.id}/"},
        },
        {
            "title": "Bienvenue dans MemoAI",
            "message": "Votre espace est prêt. Commencez par une photo, une phrase, un souvenir.",
            "notification_type": "system",
            "hours_ago": 240,
            "is_read": True,
            "data": {"url": "/journal/"},
        },
    ]

    for item in notifications:
        when = now - timedelta(hours=item["hours_ago"])
        notification = Notification.objects.create(
            user=user,
            title=item["title"],
            message=item["message"],
            notification_type=item["notification_type"],
            data=item["data"],
            is_read=item["is_read"],
            read_at=when if item["is_read"] else None,
        )
        Notification.objects.filter(pk=notification.pk).update(created_at=when)


class Command(BaseCommand):
    help = "Rebuild the complete demo@memoai.local account with local media and AI insights."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@memoai.local")
        parser.add_argument("--password", default="DemoPass123!")

    @transaction.atomic
    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options["password"]
        now = timezone.now()
        today = timezone.localdate()

        user, _ = User.objects.get_or_create(email=email)
        user.first_name = "Sophie"
        user.last_name = "Martin"
        user.avatar = static("img/avatars/a1.svg")
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_password(password)
        user.save()

        preferences, _ = UserPreferences.objects.get_or_create(user=user)
        preferences.theme = "light"
        preferences.language = "fr"
        preferences.reduce_motion = False
        preferences.gender = "undisclosed"
        preferences.profile_visibility = "private"
        preferences.onboarding_completed = True
        preferences.onboarding_completed_at = now
        preferences.daily_reminder_enabled = True
        preferences.daily_reminder_time = time(9, 0)
        preferences.weekly_summary_enabled = True
        preferences.monthly_review_enabled = True
        preferences.email_notifications = False
        preferences.ai_summaries_enabled = True
        preferences.sentiment_analysis_enabled = True
        preferences.image_generation_enabled = True
        preferences.face_recognition_consent = True
        preferences.face_recognition_consent_date = now
        preferences.auto_delete_face_embeddings = False
        preferences.save()

        _clear_demo_content(user)

        tag_by_name = {}
        for tag_spec in TAG_SPECS:
            tag_by_name[tag_spec["name"]] = Tag.objects.create(
                user=user,
                name=tag_spec["name"],
                color=tag_spec["color"],
                icon=tag_spec["icon"],
                is_ai_suggested=tag_spec["name"] in {"automne", "voyage", "souvenirs"},
            )

        entries_by_key = {}
        media_by_key = {}

        for spec in ENTRY_SPECS:
            entry_date = _entry_date(today, spec)
            entry = JournalEntry.objects.create(
                user=user,
                title=spec["title"],
                content=spec["content"],
                entry_date=entry_date,
                location=spec.get("location", ""),
                latitude=spec.get("latitude"),
                longitude=spec.get("longitude"),
                mood=spec["mood"],
                ai_status="completed",
            )
            created_at = _aware_midmorning(entry_date)
            JournalEntry.all_objects.filter(pk=entry.pk).update(
                created_at=created_at,
                updated_at=created_at,
            )
            entry.refresh_from_db()

            media_list = [
                _create_media(entry, index, media_type)
                for index, media_type in spec["media"]
            ]
            media_by_key[spec["key"]] = media_list
            entries_by_key[spec["key"]] = entry

            _create_analysis(entry, spec, media_list)

            for tag_name in spec["tags"]:
                EntryTag.objects.create(
                    entry=entry,
                    tag=tag_by_name[tag_name],
                    is_ai_generated=tag_name in spec.get("ai_tags", []),
                )

        people_by_key = {}
        for index, person_spec in enumerate(PERSON_SPECS, start=1):
            person = Person.objects.create(
                user=user,
                name=person_spec["name"],
                avatar_url=static(person_spec["avatar"]),
                face_embedding=_embedding(index),
                notes=person_spec["notes"],
                is_confirmed=person_spec["confirmed"],
            )
            created_at = now - timedelta(days=person_spec["days_ago"])
            Person.objects.filter(pk=person.pk).update(
                created_at=created_at,
                updated_at=created_at,
            )
            person.refresh_from_db()
            people_by_key[person_spec["key"]] = person

        for face_spec in FACE_SPECS:
            top, right, bottom, left = face_spec["box"]
            FaceDetection.objects.create(
                media=media_by_key[face_spec["entry"]][face_spec["media"]],
                person=people_by_key[face_spec["person"]],
                confidence=face_spec["confidence"],
                bounding_box={
                    "top": top,
                    "right": right,
                    "bottom": bottom,
                    "left": left,
                },
                is_corrected=face_spec.get("corrected", False),
            )

        _seed_notifications(user, entries_by_key)

        PasswordResetToken.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=now - timedelta(days=1),
            used=True,
        )

        entry_count = JournalEntry.objects.filter(user=user).count()
        media_count = Media.objects.filter(entry__user=user).count()
        person_count = Person.objects.filter(user=user).count()
        notification_count = Notification.objects.filter(user=user).count()

        self.stdout.write(self.style.SUCCESS(
            f"Demo account ready: {email} — {entry_count} entries, "
            f"{media_count} media, {person_count} people, "
            f"{notification_count} notifications, "
            f"{len(TAG_SPECS)} tags and {len(FACE_SPECS)} face detections."
        ))
