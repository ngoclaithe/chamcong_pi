import numpy as np
from models.embedding import Embedding
from services.face_detection import face_detector
from services.face_embedding import get_embedding_service


class RecognitionService:
    def __init__(self, config):
        self.config = config
        self.embedding_service = get_embedding_service()
        self.similarity_threshold = getattr(config, 'SIMILARITY_THRESHOLD', 0.6)
        self._embedding_cache = []
        self._cache_loaded = False

    def _load_embeddings(self):
        all_embeddings = Embedding.query.all()
        self._embedding_cache = []
        for emb in all_embeddings:
            vector = emb.get_vector()
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            self._embedding_cache.append((emb.user_id, vector))
        self._cache_loaded = True
        print(f"[Recognition] Loaded {len(self._embedding_cache)} embeddings "
              f"for {self.registered_count} users")

    def reload_embeddings(self):
        self._load_embeddings()

    def _cosine_similarity(self, a, b):
        return float(np.dot(a, b))

    def _find_best_match(self, query_embedding):
        if not self._embedding_cache:
            return None, 0.0
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_normalized = query_embedding / norm
        else:
            return None, 0.0

        user_scores = {}
        for user_id, stored_vector in self._embedding_cache:
            sim = self._cosine_similarity(query_normalized, stored_vector)
            if user_id not in user_scores:
                user_scores[user_id] = []
            user_scores[user_id].append(sim)

        # Lay trung binh top-3 similarity cho moi user
        best_user_id = None
        best_score = -1.0
        for user_id, scores in user_scores.items():
            scores_sorted = sorted(scores, reverse=True)
            top_scores = scores_sorted[:3]
            avg_score = sum(top_scores) / len(top_scores)
            if avg_score > best_score:
                best_score = avg_score
                best_user_id = user_id

        if best_score >= self.similarity_threshold:
            return best_user_id, best_score
        return None, best_score

    def recognize_frame(self, frame):
        if not self._cache_loaded:
            self._load_embeddings()

        results = []
        faces = face_detector.detect(frame)

        for face_info in faces:
            bbox = face_info['bbox']
            landmarks = face_info.get('landmarks')

            if landmarks is not None:
                embedding = self.embedding_service.get_embedding(
                    face_img=None, landmarks=landmarks, frame=frame
                )
            else:
                face_img = face_detector.crop_face(frame, bbox)
                if face_img is None:
                    continue
                embedding = self.embedding_service.get_embedding(face_img)

            user_id, confidence = self._find_best_match(embedding)
            results.append({
                'bbox': bbox,
                'user_id': user_id,
                'confidence': confidence
            })
        return results

    @property
    def is_ready(self):
        if not self._cache_loaded:
            self._load_embeddings()
        return len(self._embedding_cache) > 0

    @property
    def registered_count(self):
        if not self._cache_loaded:
            self._load_embeddings()
        return len(set(uid for uid, _ in self._embedding_cache))


_recognition_service = None


def get_recognition_service(config=None):
    global _recognition_service
    if _recognition_service is None and config is not None:
        _recognition_service = RecognitionService(config)
    return _recognition_service
