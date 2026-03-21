from extensions import db


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    confidence = db.Column(db.Float)
    photo_path = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Attendance user_id={self.user_id} at {self.timestamp}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else 'Unknown',
            'employee_code': self.user.employee_code if self.user else '',
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'confidence': round(self.confidence, 2) if self.confidence else None,
            'photo_path': self.photo_path
        }
