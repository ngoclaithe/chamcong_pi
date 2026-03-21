from extensions import db
import numpy as np


class Embedding(db.Model):
    __tablename__ = 'embeddings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    embedding = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def set_vector(self, vector):
        self.embedding = vector.astype(np.float32).tobytes()

    def get_vector(self):
        return np.frombuffer(self.embedding, dtype=np.float32)

    def __repr__(self):
        return f'<Embedding user_id={self.user_id}>'
