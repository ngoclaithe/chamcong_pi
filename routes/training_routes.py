from flask import Blueprint, render_template, jsonify, current_app
from extensions import db
from services.training_service import start_training, get_training_status

training_bp = Blueprint('training', __name__)


@training_bp.route('/')
def training_page():
    """Training panel page."""
    status = get_training_status()
    return render_template('training.html', status=status)


@training_bp.route('/start', methods=['POST'])
def start():
    """Start training (AJAX)."""
    from config import Config
    success, message = start_training(current_app._get_current_object(), db, Config)
    return jsonify({'success': success, 'message': message})


@training_bp.route('/status')
def status():
    """Get training status (AJAX polling)."""
    return jsonify(get_training_status())
