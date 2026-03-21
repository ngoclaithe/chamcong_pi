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

    def _try_open(self, source, width, height):
        """Thu mo camera, source co the la index (int) hoac path (str)."""
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            cap.release()
            return None

        # USB camera tren Pi can MJPG format de co toc do tot
        if platform.system() != 'Windows':
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, 15)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Doc thu frame de dam bao camera hoat dong
        for attempt in range(10):
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"[Camera] Opened {source}, got frame on attempt {attempt + 1}")
                return cap
            time.sleep(0.2)

        print(f"[Camera] {source} opened but no frames after 10 attempts")
        cap.release()
        return None

    def start(self, camera_index=0, width=640, height=480):
        if self.running:
            return
        self.width = width
        self.height = height

        system = platform.system()

        if system != 'Windows':
            # Linux/Pi: mo bang device path
            dev_path = f'/dev/video{camera_index}'
            print(f"[Camera] Trying {dev_path}...")
            self.camera = self._try_open(dev_path, width, height)

            # Fallback: mo bang index
            if self.camera is None:
                print(f"[Camera] Path failed, trying index {camera_index}...")
                self.camera = self._try_open(camera_index, width, height)
        else:
            # Windows: DirectShow
            print(f"[Camera] Trying DirectShow index {camera_index}...")
            self.camera = self._try_open(camera_index, width, height)

        if self.camera is None:
            raise RuntimeError(f"Cannot open camera {camera_index}")

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
        # Cho OS giai phong device
        time.sleep(0.5)

    def _capture_loop(self):
        fail_count = 0
        while self.running:
            try:
                if self.camera and self.camera.isOpened():
                    success, frame = self.camera.read()
                    if success and frame is not None:
                        frame = cv2.flip(frame, 1)
                        with self._frame_lock:
                            self.frame = frame
                        fail_count = 0
                    else:
                        fail_count += 1
                        if fail_count > 50:
                            print("[Camera] Too many read failures, stopping")
                            self.running = False
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
