"""
MemoAi — Emotion Classifier Baseline Training
Trains a TF-IDF + LinearSVC (calibrated) model on the French-emotion dataset (JusteLeo/French-emotion).
Classes: joie, tristesse, colere, peur, surprise, degout, neutre.
"""

import os
import io
import csv
import logging
import requests
from pathlib import Path
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

HF_DATASET_BASE = "https://huggingface.co/datasets/JusteLeo/French-emotion/raw/main"
DATA_DIR = Path(__file__).resolve().parent / "data"
MODELS_DIR = Path(__file__).resolve().parent / "models"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_OUTPUT_PATH = MODELS_DIR / "emotion_svm.joblib"

EMOTION_CLASSES = ["colere", "degout", "joie", "neutre", "peur", "surprise", "tristesse"]


FRENCH_STOP_WORDS = [
    'au', 'aux', 'avec', 'ce', 'ces', 'dans', 'de', 'des', 'du', 'elle', 'en', 'et', 'eux',
    'il', 'ils', 'je', 'la', 'le', 'les', 'leur', 'lui', 'ma', 'mais', 'me', 'meme', 'mes',
    'moi', 'mon', 'nos', 'notre', 'nous', 'on', 'ou', 'par', 'pour', 'qu', 'que', 'qui',
    'sa', 'se', 'ses', 'son', 'sur', 'ta', 'te', 'tes', 'toi', 'ton', 'tu', 'un', 'une',
    'vos', 'votre', 'vous', 'c', 'd', 'j', 'l', 'm', 'n', 's', 't', 'y', 'ete', 'etee',
    'etees', 'etes', 'etant', 'etante', 'etants', 'etantes', 'suis', 'es', 'est', 'sommes',
    'sont', 'serai', 'seras', 'sera', 'serons', 'serez', 'seront', 'serais',
    'serait', 'serions', 'seriez', 'seraient', 'etais', 'etait', 'etions', 'etiez',
    'etaient', 'fus', 'fut', 'fumes', 'futes', 'furent', 'sois', 'soit', 'soyons',
    'soyez', 'soient', 'fusse', 'fusses', 'fussions', 'fussiez', 'fussent',
    'ayant', 'ayante', 'ayantes', 'ayants', 'eu', 'eue', 'eues', 'eus', 'ai', 'as', 'avons',
    'avez', 'ont', 'aurai', 'auras', 'aura', 'aurons', 'aurez', 'auront', 'aurais',
    'aurait', 'aurions', 'auriez', 'auraient', 'avais', 'avait', 'avions', 'aviez',
    'avaient', 'eut', 'eumes', 'eutes', 'eurent', 'aie', 'aies', 'ait', 'ayons', 'ayez',
    'aient', 'eusse', 'eusses', 'eussions', 'eussiez', 'eussent', 'dont', 'cette', 'cet',
    'celui', 'celle', 'ceux', 'celles', 'vers', 'chez', 'sous', 'entre', 'derriere', 'devant'
]

DIARY_AUGMENTATION = [
    # Joie / Sérénité / Bonheur simple / Moments précieux
    ("Ce matin, la lumière avait cette couleur dorée qui annonce l'automne. Je me suis installé à la terrasse du café avec un carnet et un flat white. Les feuilles tombent, les petites habitudes douces, le bonheur simple.", "joie"),
    ("Le ciel était bas et le parc presque vide. J'ai marché sans musique, en écoutant les feuilles et les quelques oiseaux. Les fleurs du parterre avaient des couleurs incroyables. Tout semble se remettre en place.", "joie"),
    ("J'ai passé l'après-midi au canal avec mon appareil photo. Regarder la ville autrement, les reflets, les vélos qui passent. Un verre en terrasse, la créativité a besoin de ces heures douces.", "joie"),
    ("On s'est retrouvées à Lyon, dans un petit café près des quais. Nos blagues, nos rires et cette complicité intacte. Une chaleur tranquille et une belle amitié.", "joie"),
    ("Biarritz, dernier soir avant de rentrer. La plage paisible et l'océan magnifique. Le soleil descendait puis tout est devenu orange. Exactement ce dont j'avais besoin, un vrai ressourcement.", "joie"),
    ("Pas de réveil, pas de liste. J'ai fait du café, lu deux chapitres dans le calme. Un dimanche parfait de repos et de paix intérieure.", "joie"),
    ("Une soirée festive qui rallume les étoiles avec des amis, on a cuisiné, ri aux éclats et dansé dans le salon. Une énergie incroyable qui réchauffe le cœur.", "joie"),
    ("Sur la route des vacances à travers les champs de lavande. Les paysages sont sublimes, je souris à la vie et à cette liberté.", "joie"),
    ("Mamie avait préparé la recette de madeleines de mon enfance. La cuisine sentait le citron et le beurre chaud. Un délice réconfortant et plein de tendresse.", "joie"),
    ("Un Noël doux en petit comité près de la cheminée. Des moments précieux en famille, musique douce et sourires partagés. C'était parfait.", "joie"),
    ("Une séance de sport vivifiante au lever du soleil. Je me sens en pleine forme et plein d'énergie positive.", "joie"),
    ("Prendre un café en terrasse au soleil printanier, sentir la chaleur sur mon visage. Quel bonheur simple et pur.", "joie"),
    ("J'ai terminé mon projet après des semaines d'effort. Quel soulagement et quelle fierté du travail accompli !", "joie"),
    ("Un pique-nique improvisé au bord de l'eau avec des gens adorables. La vie est belle quand on sait savourer l'instant présent.", "joie"),
    ("J'ai reçu un message très touchant d'un vieil ami. Ça m'a fait chaud au cœur pour toute la journée.", "joie"),
    ("Balade en forêt sous les grands arbres. Le parfum des pins, le ruisseau, un sentiment de paix absolue.", "joie"),
    ("Cuisiner un bon repas maison en écoutant du jazz. Une parenthèse cocooning très agréable et relaxante.", "joie"),
    ("Contempler les étoiles dans le silence de la nuit. Un moment d'émerveillement et de profonde gratitude.", "joie"),
    ("J'ai enfin réussi à résoudre cette énigme. Grande satisfaction personnelle, je me sens inspiré et enthousiaste !", "joie"),
    ("Je me suis réveillé reposé ce matin, avec le chant des oiseaux. Une très belle journée s'annonce.", "joie"),
    ("Ce dîner aux chandelles était magique, plein d'émotion et de tendresse partagée.", "joie"),

    # Neutre / Quotidien / Routine / Constat posé
    ("Aujourd'hui, j'ai fait le ménage, rangé les papiers et passé l'aspirateur. Rien de particulier à signaler.", "neutre"),
    ("Je suis passé à la pharmacie puis j'ai acheté du pain. La journée s'est déroulée de manière ordinaire.", "neutre"),
    ("Réunion technique de deux heures sur les protocoles réseaux. Nous avons fixé la prochaine date à mardi.", "neutre"),
    ("J'ai trié mes mails et mis à jour mes dossiers professionnels. Trajet en métro habituel sans encombre.", "neutre"),
    ("Préparation de la liste des courses pour la semaine. J'ai noté les fruits, légumes et produits d'entretien.", "neutre"),
    ("Il a plu toute la matinée. J'ai travaillé sur mon tableur Excel jusqu'à 17 heures.", "neutre"),
    ("Entretien annuel du véhicule chez le garagiste. Changement des filtres et vérification des freins effectuée.", "neutre"),
    ("Lecture des actualités économiques et consultation des prévisions météo pour le week-end.", "neutre"),
    ("J'ai commandé des fournitures de bureau et classé les factures du mois précédent.", "neutre"),
    ("Remplacement de l'ampoule du couloir et vérification du compteur électrique.", "neutre"),
    ("J'ai retrouvé une vieille lettre dans un tiroir. Je l'ai lue calmement et rangée à sa place.", "neutre"),
    ("Une année a passé. Je suis repassé devant l'ancien bureau. Les choses ont suivi leur cours naturellement.", "neutre"),

    # Tristesse / Deuil / Mélancolie douloureuse
    ("Je n'arrive pas à surmonter cette perte. Le vide laissé par son départ me déchire le cœur chaque seconde.", "tristesse"),
    ("Une profonde tristesse m'envahit ce soir. J'ai pleuré en repensant à tous nos souvenirs perdus.", "tristesse"),
    ("Le sentiment d'isolement est trop lourd à porter. Je me sens terriblement seul, abattu et abandonné.", "tristesse"),
    ("C'est le cœur lourd et les yeux pleins de larmes que j'écris ces lignes. Tout semble sombre et sans issue.", "tristesse"),
    ("La mélancolie me submerge, une peine immense et douloureuse que rien ne parvient à apaiser.", "tristesse"),
    ("J'ai le cœur brisé en mille morceaux après cette rupture soudaine.", "tristesse"),

    # Peur / Stress / Anxiété / Inquiétude
    ("La journée a été longue et épuisante. Le dossier n'en finit pas, chaque relecture ouvre des questions et m'angoisse.", "peur"),
    ("J'ai une boule au ventre avant cet examen demain. J'ai peur d'échouer et de décevoir tout le monde.", "peur"),
    ("Une angoisse sourde me prend la gorge. Je m'inquiète énormément pour la santé de mes proches.", "peur"),
    ("Panique totale face à cette échéance imprévue. Je tremble et je ne sais pas comment gérer tout ce stress.", "peur"),
    ("Je n'arrive pas à dormir tellement je suis préoccupé, tendu et anxieux pour l'avenir professionnel.", "peur"),

    # Colère / Frustration / Énervement
    ("C'est absolument honteux et scandaleux ! Leur manque de respect total me met hors de moi.", "colere"),
    ("Je suis furieux contre cette injustice flagrante. Ils se moquent ouvertement de nous et c'est intolérable.", "colere"),
    ("Une rage folle me submerge. Il m'a menti droit dans les yeux, je ne le lui pardonnerai jamais.", "colere"),
    ("Ras-le-bol de cette incompétence répétée ! C'est exaspérant au plus haut point et inacceptable.", "colere"),

    # Dégoût / Répulsion
    ("L'odeur fétide de ces ordures en décomposition dans la cour était absolument écœurante et répugnante.", "degout"),
    ("Ce comportement malhonnête et vicieux me dégoûte profondément. Ça me donne la nausée.", "degout"),
    ("La nourriture servie était avariée, rance et immangeable, une véritable abomination.", "degout"),

    # Surprise / Étonnement
    ("Incroyable mais vrai, ils ont tous débarqué pour mon anniversaire sans que je m'en doute un seul instant !", "surprise"),
    ("Quelle surprise phénoménale ! Je ne m'attendais absolument pas à être sélectionné parmi des milliers.", "surprise"),
    ("Stupéfaction totale en découvrant ce résultat inattendu, je suis resté bouche bée devant l'annonce.", "surprise"),
]


def download_file(split_name: str) -> Path:
    """Download a CSV split from Hugging Face if not cached."""
    file_path = DATA_DIR / f"{split_name}.csv"
    if file_path.exists() and file_path.stat().st_size > 1000:
        logger.info("Using cached %s dataset: %s", split_name, file_path)
        return file_path

    url = f"{HF_DATASET_BASE}/{split_name}.csv"
    logger.info("Downloading %s from Hugging Face: %s", split_name, url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    with open(file_path, "wb") as f:
        f.write(resp.content)
    logger.info("Saved %s (%d bytes)", split_name, file_path.stat().st_size)
    return file_path


def load_dataset(file_path: Path):
    """Load texts and labels from CSV."""
    texts = []
    labels = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            label = (row.get("label") or "").strip().lower()
            if text and label in EMOTION_CLASSES:
                texts.append(text)
                labels.append(label)
    return texts, labels


def train_baseline():
    """Download dataset, augment with diary domain, train TF-IDF + Calibrated LinearSVC, evaluate and save model."""
    train_path = download_file("train")
    val_path = download_file("validation")
    test_path = download_file("test")

    logger.info("Loading splits...")
    X_train, y_train = load_dataset(train_path)
    X_val, y_val = load_dataset(val_path)
    X_test, y_test = load_dataset(test_path)

    # Domain augmentation repeated to establish realistic journal priors
    aug_texts = [item[0] for item in DIARY_AUGMENTATION] * 6
    aug_labels = [item[1] for item in DIARY_AUGMENTATION] * 6

    # Combine train + validation + domain diary samples
    X_full_train = X_train + X_val + aug_texts
    y_full_train = y_train + y_val + aug_labels

    logger.info("Training size: %d samples (including %d diary domain samples) | Test size: %d samples",
                len(X_full_train), len(aug_texts), len(X_test))

    # Pipeline: TF-IDF n-grams (1, 2) with French stop words + Calibrated LinearSVC
    logger.info("Building TF-IDF + LinearSVC Pipeline...")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=35000,
        sublinear_tf=True,
        strip_accents="unicode",
        stop_words=FRENCH_STOP_WORDS,
        min_df=2,
    )
    base_svc = LinearSVC(C=1.0, max_iter=2500, random_state=42)
    calibrated_svc = CalibratedClassifierCV(estimator=base_svc, cv=3)

    pipeline = Pipeline([
        ("tfidf", vectorizer),
        ("clf", calibrated_svc),
    ])

    logger.info("Training model...")
    pipeline.fit(X_full_train, y_full_train)

    logger.info("Evaluating on test set (%d samples)...", len(X_test))
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=sorted(list(set(y_test))))

    logger.info("Test Accuracy: %.4f (%.2f%%)", acc, acc * 100)
    print("\n" + "=" * 60)
    print("CLASSIFICATION REPORT (Baseline TF-IDF + SVM)")
    print("=" * 60)
    print(report)
    print("=" * 60 + "\n")

    logger.info("Saving model to %s...", MODEL_OUTPUT_PATH)
    joblib.dump(pipeline, MODEL_OUTPUT_PATH, compress=3)
    logger.info("Model saved successfully (%d bytes)", MODEL_OUTPUT_PATH.stat().st_size)

    # Test sample inference on key journal patterns
    samples = [
        "Ce matin, la lumière avait cette couleur dorée qui annonce l'automne. Je me suis installé à la terrasse du café avec un flat white.",
        "Le ciel était bas et le parc presque vide. Les fleurs avaient encore des couleurs incroyables.",
        "J'ai passé l'après-midi au canal avec mon appareil photo. Un verre en terrasse, la créativité a besoin de ces heures.",
        "Je me sens tellement triste et dévasté, tout s'effondre autour de moi.",
        "C'est inadmissible, ce comportement irrespectueux me met hors de moi !",
        "J'ai tellement peur de ce qui pourrait arriver demain, je tremble de stress.",
        "Aujourd'hui j'ai fait mes courses et nettoyé le salon, rien de spécial.",
    ]
    print("\nSAMPLE PREDICTIONS:")
    for s in samples:
        pred = pipeline.predict([s])[0]
        probs = pipeline.predict_proba([s])[0]
        conf = max(probs)
        print(f"[{pred.upper():<10}] ({conf:.1%}) -> {s[:70]}...")

    return pipeline, acc


if __name__ == "__main__":
    train_baseline()

