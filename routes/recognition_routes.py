import cv2
import time
import base64
import threading
from flask import Blueprint, render_template, jsonify, current_app, Response
from services.camera_service import camera_service
from services.recognition_service import get_recognition_service
from services.attendance_service import attendance_service
from models.user import User

recognition_bp = Blueprint('recognition', __name__)

SCAN_ZONE_RATIO = 0.55

_cached_detections = []
_detection_lock = threading.Lock()


def _update_cached_detections(results):
    global _cached_detections
    with _detection_lock:
        _cached_detections = list(results)


def _get_cached_detections():
    with _detection_lock:
        return list(_cached_detections)


def _get_scan_zone(w, h):
    zone_size = int(min(w, h) * SCAN_ZONE_RATIO)
    x1 = (w - zone_size) // 2
    y1 = (h - zone_size) // 2
    return x1, y1, x1 + zone_size, y1 + zone_size


def _draw_overlays(frame):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = _get_scan_zone(w, h)

    zone_color = (0, 255, 128)
    line_len = (x2 - x1) // 4
    thickness = 3

    cv2.rectangle(frame, (x1, y1), (x2, y2), zone_color, 1)
    cv2.line(frame, (x1, y1), (x1 + line_len, y1), zone_color, thickness)
    cv2.line(frame, (x1, y1), (x1, y1 + line_len), zone_color, thickness)
    cv2.line(frame, (x2, y1), (x2 - line_len, y1), zone_color, thickness)
    cv2.line(frame, (x2, y1), (x2, y1 + line_len), zone_color, thickness)
    cv2.line(frame, (x1, y2), (x1 + line_len, y2), zone_color, thickness)
    cv2.line(frame, (x1, y2), (x1, y2 - line_len), zone_color, thickness)
    cv2.line(frame, (x2, y2), (x2 - line_len, y2), zone_color, thickness)
    cv2.line(frame, (x2, y2), (x2, y2 - line_len), zone_color, thickness)

    detections = _get_cached_detections()
    for det in detections:
        bx, by, bw, bh = det['bbox']
        is_known = det.get('user_id') is not None
        name = det.get('name', 'Unknown')
        conf = det.get('confidence', 0)
        color = (0, 255, 128) if is_known else (0, 128, 255)

        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), color, 2)
        label = f"{name} {int(conf * 100)}%"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        (tw, th), _ = cv2.getTextSize(label, font, scale, 1)
        cv2.rectangle(frame, (bx, by - th - 8), (bx + tw + 4, by), color, -1)
        cv2.putText(frame, label, (bx + 2, by - 5), font, scale, (0, 0, 0), 1)

    return frame


@recognition_bp.route('/')
def recognition_page():
    return render_template('recognition.html')


@recognition_bp.route('/video_feed')
def recognition_video_feed():
    from services.camera_helper import start_camera_if_configured
    if not start_camera_if_configured():
        return "Camera chua duoc cau hinh. Vao /settings/ de cau hinh.", 503

    def generate():
        while camera_service.is_running:
            frame = camera_service.get_frame()
            if frame is not None:
                frame = _draw_overlays(frame)
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n'
                           + buffer.tobytes() + b'\r\n')
            time.sleep(1 / 15)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@recognition_bp.route('/detect', methods=['POST'])
def detect():
    frame = camera_service.get_frame()
    if frame is None:
        _update_cached_detections([])
        return jsonify({'success': False, 'message': 'Camera not available', 'results': []})

    from config import Config
    recognition = get_recognition_service(Config)
    if recognition is None or not recognition.is_ready:
        _update_cached_detections([])
        return jsonify({'success': False, 'message': 'Chua co nhan vien nao dang ky.', 'results': []})

    results = recognition.recognize_frame(frame)
    h, w = frame.shape[:2]
    zx1, zy1, zx2, zy2 = _get_scan_zone(w, h)

    response_results = []
    for r in results:
        bx, by, bw, bh = r['bbox']
        cx, cy = bx + bw // 2, by + bh // 2
        if not (zx1 <= cx <= zx2 and zy1 <= cy <= zy2):
            continue

        name = "Unknown"
        employee_code = ""
        logged = False

        if r['user_id'] is not None:
            user = User.query.get(r['user_id'])
            if user:
                name = user.name
                employee_code = user.employee_code
                success, _ = attendance_service.log_attendance(
                    r['user_id'], r['confidence'],
                    frame=frame, data_dir=current_app.config.get('DATA_DIR')
                )
                logged = success

        # Crop face -> base64 cho frontend
        face_b64 = None
        margin = 15
        fy1, fy2 = max(0, by - margin), min(h, by + bh + margin)
        fx1, fx2 = max(0, bx - margin), min(w, bx + bw + margin)
        face_crop = frame[fy1:fy2, fx1:fx2]
        if face_crop.size > 0:
            ret, buf = cv2.imencode('.jpg', face_crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                face_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')

        response_results.append({
            'bbox': [int(x) for x in r['bbox']],
            'user_id': int(r['user_id']) if r['user_id'] is not None else None,
            'name': name,
            'employee_code': employee_code,
            'confidence': round(float(r['confidence']), 3),
            'logged': logged,
            'face_b64': face_b64
        })

    _update_cached_detections(response_results)
    return jsonify({'success': True, 'results': response_results, 'count': len(response_results)})


@recognition_bp.route('/today', methods=['GET'])
def today_attendance():
    records = attendance_service.get_today()
    return jsonify({'success': True, 'records': [r.to_dict() for r in records]})
