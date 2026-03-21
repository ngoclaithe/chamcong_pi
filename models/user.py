from extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    employee_code = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    embeddings = db.relationship('Embedding', backref='user', lazy=True, cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.name} ({self.employee_code})>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'employee_code': self.employee_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'embedding_count': len(self.embeddings)
        }

    @staticmethod
    def generate_employee_code():
        last_user = User.query.order_by(User.id.desc()).first()
        if last_user and last_user.employee_code.startswith('NV'):
            try:
                last_num = int(last_user.employee_code[2:])
                return f'NV{last_num + 1:03d}'
            except ValueError:
                pass
        count = User.query.count()
        return f'NV{count + 1:03d}'
