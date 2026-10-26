"""
MemoAi — CamemBERT Fine-Tuning for Emotion Classification
Fine-tunes a pretrained CamemBERT model (camembert-base) on the French-emotion dataset (JusteLeo/French-emotion).
Supports 7 classes: joie, tristesse, colere, peur, surprise, degout, neutre.

Usage:
    python ai/ml/train_camembert.py --epochs 3 --batch-size 16 --lr 2e-5
"""

import os
import sys
import csv
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
MODELS_DIR = Path(__file__).resolve().parent / "models"
CAMEMBERT_OUTPUT_DIR = MODELS_DIR / "camembert_emotion"

LABEL_LIST = ["colere", "degout", "joie", "neutre", "peur", "surprise", "tristesse"]
LABEL2ID = {label: i for i, label in enumerate(LABEL_LIST)}
ID2LABEL = {i: label for i, label in enumerate(LABEL_LIST)}


def load_split_csv(split_name: str):
    file_path = DATA_DIR / f"{split_name}.csv"
    if not file_path.exists():
        from ai.ml.train_baseline import download_file
        file_path = download_file(split_name)

    texts = []
    labels = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            label = (row.get("label") or "").strip().lower()
            if text and label in LABEL2ID:
                texts.append(text)
                labels.append(LABEL2ID[label])
    return texts, labels


def train_camembert(args):
    try:
        import torch
        from transformers import (
            AutoTokenizer,
            AutoModelForSequenceClassification,
            Trainer,
            TrainingArguments,
            DataCollatorWithPadding,
        )
    except ImportError:
        logger.error(
            "Transformers and PyTorch are required for CamemBERT fine-tuning.\n"
            "Please run: pip install torch transformers datasets accelerate"
        )
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() and not args.cpu else "cpu"
    logger.info("Using device: %s", device)

    model_name = args.pretrained_model
    logger.info("Loading tokenizer for %s...", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    logger.info("Loading dataset splits from %s...", DATA_DIR)
    train_texts, train_labels = load_split_csv("train")
    val_texts, val_labels = load_split_csv("validation")
    test_texts, test_labels = load_split_csv("test")

    if args.max_samples:
        logger.info("Limiting to %d samples for quick run", args.max_samples)
        train_texts, train_labels = train_texts[:args.max_samples], train_labels[:args.max_samples]
        val_texts, val_labels = val_texts[:min(len(val_texts), args.max_samples // 4)], val_labels[:min(len(val_labels), args.max_samples // 4)]

    logger.info("Train: %d | Val: %d | Test: %d", len(train_texts), len(val_texts), len(test_texts))

    class EmotionDataset(torch.utils.data.Dataset):
        def __init__(self, encodings, labels):
            self.encodings = encodings
            self.labels = labels

        def __getitem__(self, idx):
            item = {key: val[idx].clone().detach() for key, val in self.encodings.items()}
            item["labels"] = torch.tensor(self.labels[idx])
            return item

        def __len__(self):
            return len(self.labels)

    logger.info("Tokenizing texts...")
    train_encodings = tokenizer(train_texts, truncation=True, max_length=args.max_length, padding=True, return_tensors="pt")
    val_encodings = tokenizer(val_texts, truncation=True, max_length=args.max_length, padding=True, return_tensors="pt")
    test_encodings = tokenizer(test_texts, truncation=True, max_length=args.max_length, padding=True, return_tensors="pt")

    train_dataset = EmotionDataset(train_encodings, train_labels)
    val_dataset = EmotionDataset(val_encodings, val_labels)
    test_dataset = EmotionDataset(test_encodings, test_labels)

    logger.info("Initializing CamemBERT model with 7 classes...")
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(LABEL_LIST),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        preds = predictions.argmax(-1)
        acc = (preds == labels).mean()
        return {"accuracy": float(acc)}

    training_args = TrainingArguments(
        output_dir=str(CAMEMBERT_OUTPUT_DIR / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_steps=50,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        learning_rate=args.lr,
        fp16=torch.cuda.is_available() and not args.cpu,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        tokenizer=tokenizer,
    )

    logger.info("Starting fine-tuning...")
    trainer.train()

    logger.info("Evaluating on test set...")
    test_results = trainer.evaluate(test_dataset)
    logger.info("Test results: %s", test_results)

    CAMEMBERT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Saving best model and tokenizer to %s...", CAMEMBERT_OUTPUT_DIR)
    model.save_pretrained(str(CAMEMBERT_OUTPUT_DIR))
    tokenizer.save_pretrained(str(CAMEMBERT_OUTPUT_DIR))
    logger.info("CamemBERT fine-tuning completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune CamemBERT for emotion classification.")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size per device")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--max-length", type=int, default=128, help="Max sequence length")
    parser.add_argument("--pretrained-model", type=str, default="camembert-base", help="Hugging Face base model")
    parser.add_argument("--max-samples", type=int, default=None, help="Limit samples for quick test")
    parser.add_argument("--cpu", action="store_true", help="Force CPU training")
    args = parser.parse_args()

    train_camembert(args)
