import os
import cv2
from datetime import datetime, timedelta, date
from extensions import db
from models.attendance import Attendance
from models.user import User


class AttendanceService:
    def __init__(self, duplicate_window_minutes=5):
        self.duplicate_window = timedelta(minutes=duplicate_window_minutes)

    def log_attendance(self, user_id, confidence=None, frame=None, data_dir=None):
        cutoff = datetime.now() - self.duplicate_window
        recent = Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.timestamp >= cutoff
        ).first()
        if recent:
            return False, "Already logged recently"

        photo_path = None
        if frame is not None and data_dir is not None:
            photo_dir = os.path.join(data_dir, 'attendance_photos')
            os.makedirs(photo_dir, exist_ok=True)
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'user_{user_id}_{timestamp_str}.jpg'
            cv2.imwrite(os.path.join(photo_dir, filename), frame)
            photo_path = f'attendance_photos/{filename}'

        record = Attendance(user_id=user_id, confidence=confidence, photo_path=photo_path)
        db.session.add(record)
        db.session.commit()

        user = User.query.get(user_id)
        return True, f"Attendance logged for {user.name if user else 'Unknown'}"

    def delete_record(self, record_id, data_dir=None):
        record = Attendance.query.get(record_id)
        if not record:
            return False, "Record not found"
        if record.photo_path and data_dir:
            photo_full_path = os.path.join(data_dir, record.photo_path)
            if os.path.exists(photo_full_path):
                os.remove(photo_full_path)
        db.session.delete(record)
        db.session.commit()
        return True, "Record deleted"

    def delete_all(self, data_dir=None):
        count = Attendance.query.count()
        if data_dir:
            photo_dir = os.path.join(data_dir, 'attendance_photos')
            if os.path.exists(photo_dir):
                import shutil
                shutil.rmtree(photo_dir, ignore_errors=True)
                os.makedirs(photo_dir, exist_ok=True)
        Attendance.query.delete()
        db.session.commit()
        return True, count

    def get_today(self):
        today_start = datetime.combine(date.today(), datetime.min.time())
        return Attendance.query.filter(
            Attendance.timestamp >= today_start
        ).order_by(Attendance.timestamp.desc()).all()

    def get_by_date(self, target_date):
        start = datetime.combine(target_date, datetime.min.time())
        end = start + timedelta(days=1)
        return Attendance.query.filter(
            Attendance.timestamp >= start, Attendance.timestamp < end
        ).order_by(Attendance.timestamp.desc()).all()

    def get_by_range(self, start_date, end_date):
        start = datetime.combine(start_date, datetime.min.time())
        end = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)
        return Attendance.query.filter(
            Attendance.timestamp >= start, Attendance.timestamp < end
        ).order_by(Attendance.timestamp.desc()).all()

    def get_count_today(self):
        today_start = datetime.combine(date.today(), datetime.min.time())
        count = db.session.query(
            db.func.count(db.func.distinct(Attendance.user_id))
        ).filter(Attendance.timestamp >= today_start).scalar()
        return count or 0

    def export_csv(self, records):
        lines = ["STT,Ten,Ma NV,Thoi gian,Do tin cay"]
        for i, record in enumerate(records, 1):
            user = User.query.get(record.user_id)
            name = user.name if user else "Unknown"
            code = user.employee_code if user else ""
            time_str = record.timestamp.strftime("%Y-%m-%d %H:%M:%S") if record.timestamp else ""
            conf = f"{record.confidence:.2f}" if record.confidence else ""
            lines.append(f"{i},{name},{code},{time_str},{conf}")
        return "\n".join(lines)


attendance_service = AttendanceService()
