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


def _get_linux_video_devices():
    """Tim cac video capture device thuc su tren Linux/Pi."""
    devices = []
    v4l_path = '/sys/class/video4linux'
    if not os.path.exists(v4l_path):
        return devices

    # Ten cua cac node ISP/codec cua Pi, khong phai camera thuc
    pi_internal = ('bcm2835', 'rpivid', 'unicam', 'isp', 'codec')

    for dev_name in sorted(os.listdir(v4l_path)):
        dev_path = f'/dev/{dev_name}'
        if not os.path.exists(dev_path):
            continue

        name_path = os.path.join(v4l_path, dev_name, 'name')

        # Kiem tra index - chi lay index=0 (video capture), bo index>0 (metadata)
        index_path = os.path.join(v4l_path, dev_name, 'index')
        try:
            with open(index_path, 'r') as f:
                idx = int(f.read().strip())
            if idx != 0:
                continue
        except (FileNotFoundError, ValueError):
            pass

        name = dev_name
        if os.path.exists(name_path):
            try:
                with open(name_path, 'r') as f:
                    name = f.read().strip()
            except Exception:
                pass

        # Bo qua cac node ISP/codec noi bo cua Pi
        name_lower = name.lower()
        if any(kw in name_lower for kw in pi_internal):
            continue

        # Lay so index tu ten device (video0 -> 0, video2 -> 2)
        try:
            dev_index = int(dev_name.replace('video', ''))
        except ValueError:
            continue

        devices.append({'dev_path': dev_path, 'index': dev_index, 'name': name})

    return devices


def detect_cameras(max_index=10):
    cameras = []
    system = platform.system()

    old_log = os.environ.get('OPENCV_LOG_LEVEL', '')
    os.environ['OPENCV_LOG_LEVEL'] = 'FATAL'

    if system == 'Linux':
        # Tren Linux/Pi: chi scan device thuc su tu /sys/class/video4linux
        devices = _get_linux_video_devices()
        for dev in devices:
            try:
                cap = cv2.VideoCapture(dev['index'], cv2.CAP_V4L2)
                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cameras.append({
                        'index': dev['index'],
                        'name': dev['name'],
                        'width': w,
                        'height': h,
                    })
                    cap.release()
                else:
                    cap.release()
            except Exception:
                continue
    else:
        # Windows: thu DirectShow truoc
        for i in range(max_index):
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
