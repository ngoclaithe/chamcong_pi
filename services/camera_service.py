import cv2
import platform
import threading
import time


class CameraService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.camera = None
        self.frame = None
        self.running = False
        self._thread = None
        self._frame_lock = threading.Lock()
        self.width = 640
        self.height = 480

    def _get_backend(self):
        system = platform.system()
        if system == 'Windows':
            return cv2.CAP_DSHOW
        else:
            return cv2.CAP_V4L2

    def start(self, camera_index=0, width=640, height=480):
        if self.running:
            return
        self.width = width
        self.height = height
        backend = self._get_backend()
        self.camera = cv2.VideoCapture(camera_index, backend)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.camera.set(cv2.CAP_PROP_FPS, 15)
        if not self.camera.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_index}")
        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self.camera:
            self.camera.release()
            self.camera = None
        self.frame = None

    def _capture_loop(self):
        while self.running:
            try:
                if self.camera and self.camera.isOpened():
                    success, frame = self.camera.read()
                    if success:
                        frame = cv2.flip(frame, 1)
                        with self._frame_lock:
                            self.frame = frame
                    else:
                        time.sleep(0.01)
                else:
                    time.sleep(0.1)
            except Exception:
                time.sleep(0.05)

    def get_frame(self):
        with self._frame_lock:
            if self.frame is not None:
                return self.frame.copy()
        return None

    def get_jpeg(self, quality=80):
        frame = self.get_frame()
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if ret:
                return buffer.tobytes()
        return None

    def generate_mjpeg(self):
        while self.running:
            jpeg = self.get_jpeg()
            if jpeg:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n'
                       + jpeg + b'\r\n')
            time.sleep(1 / 15)

    @property
    def is_running(self):
        return self.running


camera_service = CameraService()
