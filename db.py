from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
import uuid
db = SQLAlchemy()


class User (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    phash =  db.Column(db.String(128))
    def validate_password(self, password):
        return check_password_hash(self.phash, password)


def add_user (username):
    new_user = User()
    new_user.username=username
    pw=uuid.uuid4().hex
    new_user.phash=generate_password_hash (pw)
    db.session.add(new_user)
    db.session.commit()
    return pw