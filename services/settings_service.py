import os
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


def detect_cameras():
    system = platform.system()
    cameras = []

    if system == 'Linux':
        # Doc tu sysfs, KHONG mo camera de tranh conflict
        v4l_path = '/sys/class/video4linux'
        if not os.path.exists(v4l_path):
            return cameras

        pi_internal = ('bcm2835', 'rpivid', 'unicam', 'isp', 'pispbe', 'rpi-')

        for dev_name in sorted(os.listdir(v4l_path)):
            # Chi lay index=0 devices (capture, khong phai metadata)
            index_path = os.path.join(v4l_path, dev_name, 'index')
            try:
                with open(index_path, 'r') as f:
                    if int(f.read().strip()) != 0:
                        continue
            except (FileNotFoundError, ValueError):
                pass

            # Doc ten device
            name_path = os.path.join(v4l_path, dev_name, 'name')
            name = dev_name
            try:
                with open(name_path, 'r') as f:
                    name = f.read().strip()
            except Exception:
                pass

            # Bo qua cac node noi bo cua Pi
            if any(kw in name.lower() for kw in pi_internal):
                continue

            try:
                dev_index = int(dev_name.replace('video', ''))
            except ValueError:
                continue

            cameras.append({
                'index': dev_index,
                'name': name,
                'width': 640,
                'height': 480,
            })
    else:
        # Windows: phai thu mo camera
        old_log = os.environ.get('OPENCV_LOG_LEVEL', '')
        os.environ['OPENCV_LOG_LEVEL'] = 'FATAL'

        for i in range(5):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cameras.append({
                        'index': i,
                        'name': f'Camera {i} (DirectShow)',
                        'width': w,
                        'height': h,
                    })
                    cap.release()
                else:
                    cap.release()
            except Exception:
                continue

        os.environ['OPENCV_LOG_LEVEL'] = old_log

    return cameras
