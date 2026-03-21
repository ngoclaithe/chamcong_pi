import numpy as np
from uniface import ArcFace


class FaceEmbeddingService:
    def __init__(self):
        print("[FaceEmbedding] Loading UniFace ArcFace...")
        self.recognizer = ArcFace(providers=["CPUExecutionProvider"])
        print("[FaceEmbedding] ArcFace ready")

    def get_embedding(self, face_img, landmarks=None, frame=None):
        if landmarks is not None and frame is not None:
            embedding = self.recognizer.get_normalized_embedding(frame, landmarks)
        else:
            h, w = face_img.shape[:2]
            dummy_landmarks = np.array([
                [w * 0.3, h * 0.35],
                [w * 0.7, h * 0.35],
                [w * 0.5, h * 0.55],
                [w * 0.35, h * 0.75],
                [w * 0.65, h * 0.75],
            ], dtype=np.float32)
            embedding = self.recognizer.get_normalized_embedding(face_img, dummy_landmarks)
        return embedding.flatten()

    def get_embeddings_batch(self, face_images):
        if not face_images:
            return np.array([])
        return np.array([self.get_embedding(img) for img in face_images])


_embedding_service = None


def get_embedding_service(model_path=None):
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = FaceEmbeddingService()
    return _embedding_service
