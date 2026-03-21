from models.setting import Setting


def is_camera_configured():
    return Setting.query.get('camera_index') is not None


def start_camera_if_configured():
    from services.camera_service import camera_service
    if camera_service.is_running:
        return True
    if not is_camera_configured():
        return False
    from services import settings_service
    try:
        camera_service.start(
            camera_index=settings_service.get('camera_index', 0),
            width=settings_service.get('camera_width', 640),
            height=settings_service.get('camera_height', 480)
        )
        return True
    except RuntimeError:
        return False
