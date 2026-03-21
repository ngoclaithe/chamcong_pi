import platform
import cv2

DEFAULTS = {
    'camera_index': 0,
    'camera_width': 640,
    'camera_height': 480,
    'similarity_threshold': 0.6,
    'duplicate_window_minutes': 5,
    'capture_count': 3,
    'min_capture_count': 1,
}


def get(key, default=None):
    from models.setting import Setting
    val = Setting.get(key)
    return val if val is not None else (default if default is not None else DEFAULTS.get(key))


def get_all():
    from models.setting import Setting
    return Setting.get_all()


def update(new_settings):
    from models.setting import Setting
    Setting.update_all(new_settings)
    return get_all()


def detect_cameras(max_index=10):
    import os
    cameras = []
    system = platform.system()

    # Suppress OpenCV warnings khi scan
    old_log = os.environ.get('OPENCV_LOG_LEVEL', '')
    os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

    backends = []
    if system == 'Windows':
        backends = [(cv2.CAP_DSHOW, 'DirectShow'), (cv2.CAP_MSMF, 'MSMF')]
    else:
        backends = [(cv2.CAP_V4L2, 'V4L2'), (cv2.CAP_ANY, 'Default')]

    found_indices = set()
    for backend, backend_name in backends:
        for i in range(max_index):
            if i in found_indices:
                continue
            try:
                cap = cv2.VideoCapture(i, backend)
                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    name = f"Camera {i}"
                    if system == 'Linux':
                        import os
                        dev_path = f"/sys/class/video4linux/video{i}/name"
                        if os.path.exists(dev_path):
                            with open(dev_path, 'r') as f:
                                name = f.read().strip()
                    else:
                        name = f"Camera {i} ({backend_name})"
                    cameras.append({'index': i, 'name': name, 'width': w, 'height': h})
                    found_indices.add(i)
                    cap.release()
                else:
                    cap.release()
            except Exception:
                continue

    os.environ['OPENCV_LOG_LEVEL'] = old_log

    return cameras
