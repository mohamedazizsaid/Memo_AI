"""
MemoAi — Train Emotion Model Command
Runs training of the emotion classification models (TF-IDF + SVM baseline or CamemBERT).

Usage:
    python manage.py train_emotion_model --model=svm
    python manage.py train_emotion_model --model=camembert --epochs=3
"""

from django.core.management.base import BaseCommand
import sys


class Command(BaseCommand):
    help = "Train the French emotion classification model (SVM baseline or CamemBERT)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='svm',
            choices=['svm', 'camembert'],
            help='Model architecture to train (default: svm).',
        )
        parser.add_argument(
            '--epochs',
            type=int,
            default=3,
            help='Epochs for CamemBERT training (default: 3).',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=16,
            help='Batch size for CamemBERT training (default: 16).',
        )

    def handle(self, *args, **options):
        model_choice = options.get('model', 'svm')

        if model_choice == 'svm':
            self.stdout.write(self.style.NOTICE("Training TF-IDF + Calibrated LinearSVC baseline on French-emotion..."))
            from ai.ml.train_baseline import train_baseline
            pipeline, acc = train_baseline()
            self.stdout.write(self.style.SUCCESS(f"Baseline SVM trained successfully with accuracy: {acc:.2%}"))
        elif model_choice == 'camembert':
            self.stdout.write(self.style.NOTICE("Fine-tuning CamemBERT on French-emotion..."))
            from ai.ml.train_camembert import train_camembert
            class Args:
                pass
            c_args = Args()
            c_args.epochs = options.get('epochs', 3)
            c_args.batch_size = options.get('batch_size', 16)
            c_args.lr = 2e-5
            c_args.max_length = 128
            c_args.pretrained_model = 'camembert-base'
            c_args.max_samples = None
            c_args.cpu = False
            train_camembert(c_args)
            self.stdout.write(self.style.SUCCESS("CamemBERT fine-tuning completed!"))
