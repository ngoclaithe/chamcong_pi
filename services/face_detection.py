import cv2
from uniface import RetinaFace


class FaceDetector:
    def __init__(self):
        print("[FaceDetector] Loading UniFace RetinaFace...")
        self.detector = RetinaFace(providers=["CPUExecutionProvider"])
        print("[FaceDetector] RetinaFace ready")

    def detect(self, frame, min_confidence=0.5):
        faces_raw = self.detector.detect(frame)
        results = []
        for face in faces_raw:
            conf = float(face.confidence)
            if conf < min_confidence:
                continue
            x1, y1, x2, y2 = [int(v) for v in face.bbox]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            face_w, face_h = x2 - x1, y2 - y1
            if face_w > 20 and face_h > 20:
                results.append({
                    'bbox': (x1, y1, face_w, face_h),
                    'confidence': conf,
                    'landmarks': face.landmarks if hasattr(face, 'landmarks') else None,
                    '_raw': face
                })
        return results

    def crop_face(self, frame, bbox, target_size=(112, 112), margin=0.2):
        if isinstance(bbox, dict):
            x, y, w, h = bbox['bbox']
        else:
            x, y, w, h = bbox
        fh, fw = frame.shape[:2]
        mx, my = int(w * margin), int(h * margin)
        x1, y1 = max(0, x - mx), max(0, y - my)
        x2, y2 = min(fw, x + w + mx), min(fh, y + h + my)
        face = frame[y1:y2, x1:x2]
        if face.size == 0:
            return None
        return cv2.resize(face, target_size)


face_detector = FaceDetector()
