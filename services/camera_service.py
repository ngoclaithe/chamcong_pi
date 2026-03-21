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
        if platform.system() == 'Windows':
            return cv2.CAP_DSHOW
        return cv2.CAP_V4L2

    def _try_open(self, camera_index, width, height, backend):
        """Thu mo camera voi backend cu the, return True neu doc duoc frame."""
        cap = cv2.VideoCapture(camera_index, backend)
        if not cap.isOpened():
            cap.release()
            return None

        # USB camera tren Pi can MJPG format
        if platform.system() != 'Windows':
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, 15)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Doc thu 1 frame de dam bao camera hoat dong
        for _ in range(5):
            ret, frame = cap.read()
            if ret and frame is not None:
                return cap
            time.sleep(0.1)

        cap.release()
        return None

    def start(self, camera_index=0, width=640, height=480):
        if self.running:
            return
        self.width = width
        self.height = height

        # Thu backend chinh truoc
        backend = self._get_backend()
        self.camera = self._try_open(camera_index, width, height, backend)

        # Fallback: thu CAP_ANY
        if self.camera is None and backend != cv2.CAP_ANY:
            print(f"[Camera] {backend} failed, trying CAP_ANY...")
            self.camera = self._try_open(camera_index, width, height, cv2.CAP_ANY)

        if self.camera is None:
            raise RuntimeError(f"Cannot open camera {camera_index}")

        print(f"[Camera] Started: index={camera_index}, "
              f"{int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
              f"{int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

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
                    if success and frame is not None:
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
