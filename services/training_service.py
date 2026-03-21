import threading
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from services.classifier import FaceClassifier, reload_classifier

# Global training status
training_status = {
    "running": False,
    "progress": 0,
    "epoch": 0,
    "total_epochs": 0,
    "loss": 0.0,
    "message": "Idle",
    "error": None
}


def get_training_status():
    return training_status.copy()


def start_training(app, db, config):
    """Start training in a background thread."""
    if training_status["running"]:
        return False, "Training is already in progress"

    thread = threading.Thread(target=_train_worker, args=(app, db, config), daemon=True)
    thread.start()
    return True, "Training started"


def _train_worker(app, db, config):
    """Background worker for training the classifier."""
    global training_status

    training_status.update({
        "running": True,
        "progress": 0,
        "epoch": 0,
        "total_epochs": config.TRAIN_EPOCHS,
        "loss": 0.0,
        "message": "Loading embeddings...",
        "error": None
    })

    try:
        with app.app_context():
            from models.embedding import Embedding

            # Load all embeddings from DB
            all_embeddings = Embedding.query.all()

            if len(all_embeddings) == 0:
                training_status.update({
                    "running": False,
                    "message": "No embeddings found. Please register users first.",
                    "error": "no_data"
                })
                return

            # Group by user_id
            user_ids = sorted(set(e.user_id for e in all_embeddings))
            num_classes = len(user_ids)

            if num_classes < 2:
                training_status.update({
                    "running": False,
                    "message": "Need at least 2 users to train. Currently have: " + str(num_classes),
                    "error": "insufficient_data"
                })
                return

            # Build label maps
            label_map = {idx: uid for idx, uid in enumerate(user_ids)}
            reverse_map = {uid: idx for idx, uid in enumerate(user_ids)}

            # Build training data
            X = []
            y = []
            for emb in all_embeddings:
                vector = emb.get_vector()
                label = reverse_map[emb.user_id]
                X.append(vector)
                y.append(label)

            X = np.array(X, dtype=np.float32)
            y = np.array(y, dtype=np.int64)

            training_status["message"] = f"Training with {len(X)} samples, {num_classes} classes..."

            # Create model
            model = FaceClassifier(num_classes)
            device = torch.device('cpu')
            model.to(device)
            model.train()

            # Create DataLoader
            dataset = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
            dataloader = DataLoader(
                dataset,
                batch_size=config.TRAIN_BATCH_SIZE,
                shuffle=True
            )

            # Training loop
            optimizer = torch.optim.Adam(model.parameters(), lr=config.TRAIN_LR)
            criterion = nn.CrossEntropyLoss()
            epochs = config.TRAIN_EPOCHS

            for epoch in range(epochs):
                epoch_loss = 0.0
                num_batches = 0

                for batch_X, batch_y in dataloader:
                    batch_X = batch_X.to(device)
                    batch_y = batch_y.to(device)

                    optimizer.zero_grad()
                    logits = model(batch_X)
                    loss = criterion(logits, batch_y)
                    loss.backward()
                    optimizer.step()

                    epoch_loss += loss.item()
                    num_batches += 1

                avg_loss = epoch_loss / max(num_batches, 1)
                progress = int((epoch + 1) / epochs * 100)

                training_status.update({
                    "epoch": epoch + 1,
                    "progress": progress,
                    "loss": round(avg_loss, 4),
                    "message": f"Epoch {epoch + 1}/{epochs} — Loss: {avg_loss:.4f}"
                })

                time.sleep(0.1)  # Small delay for UI updates

            # Save model
            checkpoint = {
                'num_classes': num_classes,
                'label_map': label_map,
                'reverse_map': reverse_map,
                'model_state_dict': model.state_dict()
            }
            torch.save(checkpoint, config.CLASSIFIER_PATH)

            # Reload global classifier
            reload_classifier(config.CLASSIFIER_PATH)

            training_status.update({
                "running": False,
                "progress": 100,
                "message": f"Training complete! {num_classes} classes, final loss: {avg_loss:.4f}",
                "error": None
            })

    except Exception as e:
        training_status.update({
            "running": False,
            "progress": 0,
            "message": f"Training failed: {str(e)}",
            "error": str(e)
        })
