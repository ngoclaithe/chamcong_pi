from flask import Blueprint, render_template, Response
from services.camera_service import camera_service
from services.attendance_service import attendance_service
from services.camera_helper import start_camera_if_configured, is_camera_configured
from models.user import User

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def dashboard():
    total_users = User.query.count()
    attendance_today = attendance_service.get_count_today()
    recent_attendance = attendance_service.get_today()[:10]
    camera_ready = is_camera_configured()

    from config import Config
    from services.recognition_service import get_recognition_service
    recognition = get_recognition_service(Config)
    model_ready = recognition.is_ready if recognition else False

    return render_template('dashboard.html',
                           total_users=total_users,
                           attendance_today=attendance_today,
                           recent_attendance=recent_attendance,
                           model_ready=model_ready,
                           camera_ready=camera_ready)


@main_bp.route('/video_feed')
def video_feed():
    if not start_camera_if_configured():
        return "Camera chua duoc cau hinh. Vao /settings/ de cau hinh.", 503

    return Response(
        camera_service.generate_mjpeg(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
