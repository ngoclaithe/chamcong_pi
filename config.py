import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DEFAULTS = {
    'camera_index': 0,
    'camera_width': 640,
    'camera_height': 480,
    'similarity_threshold': 0.6,
    'duplicate_window_minutes': 5,
    'capture_count': 3,
    'min_capture_count': 1,
}


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chamcong-pi-secret-key-2026')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'chamcong.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DATA_DIR = os.path.join(BASE_DIR, 'data')
    FACES_DIR = os.path.join(DATA_DIR, 'faces')

    # Gia tri mac dinh, se bi ghi de boi settings trong DB khi runtime
    CAMERA_INDEX = DEFAULTS['camera_index']
    CAMERA_WIDTH = DEFAULTS['camera_width']
    CAMERA_HEIGHT = DEFAULTS['camera_height']
    SIMILARITY_THRESHOLD = DEFAULTS['similarity_threshold']
    DUPLICATE_WINDOW_MINUTES = DEFAULTS['duplicate_window_minutes']
    CAPTURE_COUNT = DEFAULTS['capture_count']
    MIN_CAPTURE_COUNT = DEFAULTS['min_capture_count']
