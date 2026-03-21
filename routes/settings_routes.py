import platform
import sys
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from services import settings_service
from services.camera_service import camera_service

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
def settings_page():
    settings = settings_service.get_all()
    return render_template('settings.html', settings=settings,
                           platform=platform.platform(), python_version=sys.version.split()[0])


@settings_bp.route('/save', methods=['POST'])
def save_settings():
    if request.is_json:
        data = request.get_json()
    else:
        data = {
            'camera_index': int(request.form.get('camera_index', 0)),
            'camera_width': int(request.form.get('camera_width', 640)),
            'camera_height': int(request.form.get('camera_height', 480)),
            'similarity_threshold': float(request.form.get('similarity_threshold', 0.6)),
            'duplicate_window_minutes': int(request.form.get('duplicate_window_minutes', 5)),
            'capture_count': int(request.form.get('capture_count', 3)),
            'min_capture_count': int(request.form.get('min_capture_count', 1)),
        }

    settings_service.update(data)

    if camera_service.is_running:
        camera_service.stop()

    if request.is_json:
        return jsonify({'success': True, 'message': 'Da luu cau hinh.'})

    flash('Da luu cau hinh thanh cong!', 'success')
    return redirect(url_for('settings.settings_page'))


@settings_bp.route('/detect_cameras', methods=['GET'])
def detect_cameras():
    cameras = settings_service.detect_cameras()
    return jsonify({'success': True, 'cameras': cameras})
