import torch
import torch.nn as nn
import numpy as np
import os


class FaceClassifier(nn.Module):
    """Simple linear classifier: 128-dim embedding -> num_classes."""

    def __init__(self, num_classes):
        super().__init__()
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        return self.fc(x)


class ClassifierService:
    """Manage the face classifier: load, save, predict."""

    def __init__(self, classifier_path=None):
        self.classifier_path = classifier_path
        self.model = None
        self.label_map = {}  # idx -> user_id
        self.reverse_map = {}  # user_id -> idx
        self.num_classes = 0
        self.device = torch.device('cpu')
        self._load()

    def _load(self):
        """Load classifier from disk if exists."""
        if self.classifier_path and os.path.exists(self.classifier_path):
            try:
                checkpoint = torch.load(self.classifier_path, map_location=self.device)
                self.num_classes = checkpoint['num_classes']
                self.label_map = checkpoint['label_map']
                self.reverse_map = checkpoint.get('reverse_map', {v: k for k, v in self.label_map.items()})
                self.model = FaceClassifier(self.num_classes)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.model.to(self.device)
                self.model.eval()
                print(f"[Classifier] Loaded model with {self.num_classes} classes")
            except Exception as e:
                print(f"[Classifier] Failed to load: {e}")
                self.model = None

    def save(self):
        """Save classifier to disk."""
        if self.model and self.classifier_path:
            checkpoint = {
                'num_classes': self.num_classes,
                'label_map': self.label_map,
                'reverse_map': self.reverse_map,
                'model_state_dict': self.model.state_dict()
            }
            os.makedirs(os.path.dirname(self.classifier_path), exist_ok=True)
            torch.save(checkpoint, self.classifier_path)
            print(f"[Classifier] Saved to {self.classifier_path}")

    def predict(self, embedding):
        """
        Predict user_id from embedding.
        Returns: (user_id, confidence) or (None, 0.0)
        """
        if self.model is None or self.num_classes == 0:
            return None, 0.0

        tensor = torch.from_numpy(embedding.astype(np.float32)).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)
            confidence, idx = torch.max(probs, dim=1)

        idx = idx.item()
        confidence = confidence.item()
        user_id = self.label_map.get(idx)

        return user_id, confidence

    @property
    def is_ready(self):
        return self.model is not None and self.num_classes > 0


# Global instance (lazy loaded)
_classifier_service = None


def get_classifier_service(classifier_path=None):
    global _classifier_service
    if _classifier_service is None:
        _classifier_service = ClassifierService(classifier_path)
    return _classifier_service


def reload_classifier(classifier_path):
    """Force reload classifier (after training)."""
    global _classifier_service
    _classifier_service = ClassifierService(classifier_path)
    return _classifier_service
