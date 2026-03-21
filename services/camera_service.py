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

    def start(self, camera_index=0, width=640, height=480):
        if self.running:
            return

        print(f"[Camera] Opening index {camera_index}...")

        # Dung cach don gian nhat: cv2.VideoCapture(index)
        self.camera = cv2.VideoCapture(camera_index)

        if not self.camera.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_index}")

        # Set MJPG truoc resolution (USB camera tren Pi can MJPG)
        if platform.system() != 'Windows':
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.camera.set(cv2.CAP_PROP_FPS, 15)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Doc thu 1 frame
        ret, frame = self.camera.read()
        if not ret:
            self.camera.release()
            raise RuntimeError(f"Camera {camera_index} opened but cannot read frames")

        actual_w = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[Camera] Started: index={camera_index}, {actual_w}x{actual_h}")

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
        time.sleep(0.5)

    def _capture_loop(self):
        while self.running:
            try:
                if self.camera and self.camera.isOpened():
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
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
            ret, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if ret:
                return buf.tobytes()
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
