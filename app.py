import os
from flask import Flask, send_from_directory
from extensions import db
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(Config.DATA_DIR, exist_ok=True)
    os.makedirs(Config.FACES_DIR, exist_ok=True)
    os.makedirs(os.path.join(Config.DATA_DIR, 'attendance_photos'), exist_ok=True)

    db.init_app(app)

    from routes.main_routes import main_bp
    from routes.user_routes import user_bp
    from routes.training_routes import training_bp
    from routes.recognition_routes import recognition_bp
    from routes.attendance_routes import attendance_bp
    from routes.settings_routes import settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(training_bp, url_prefix='/training')
    app.register_blueprint(recognition_bp, url_prefix='/recognition')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    @app.route('/data/<path:filename>')
    def serve_data_file(filename):
        return send_from_directory(Config.DATA_DIR, filename)

    @app.template_filter('urlencode_pagination')
    def urlencode_pagination(args, page):
        from urllib.parse import urlencode
        params = dict(args)
        params['page'] = page
        return urlencode(params)

    with app.app_context():
        from models import User, Embedding, Attendance, Setting  # noqa: F401
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
