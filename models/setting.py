import json
from extensions import db


class Setting(db.Model):
    __tablename__ = 'settings'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    @staticmethod
    def get(key, default=None):
        row = Setting.query.get(key)
        if row is None:
            return default
        try:
            return json.loads(row.value)
        except (json.JSONDecodeError, TypeError):
            return row.value

    @staticmethod
    def set(key, value):
        row = Setting.query.get(key)
        if row:
            row.value = json.dumps(value)
        else:
            row = Setting(key=key, value=json.dumps(value))
            db.session.add(row)
        db.session.commit()

    @staticmethod
    def get_all():
        from services.settings_service import DEFAULTS
        result = dict(DEFAULTS)
        for row in Setting.query.all():
            try:
                result[row.key] = json.loads(row.value)
            except (json.JSONDecodeError, TypeError):
                result[row.key] = row.value
        return result

    @staticmethod
    def update_all(data):
        for key, value in data.items():
            row = Setting.query.get(key)
            if row:
                row.value = json.dumps(value)
            else:
                row = Setting(key=key, value=json.dumps(value))
                db.session.add(row)
        db.session.commit()
