from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import datetime
from tools import *
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    password_hash = db.Column(db.String(128))
    records = db.relationship('Record')
    allowed = db.Column(db.Boolean, default=False)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)


class AccountApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', uselist=False, backref='AccountApplication')
    allowed = db.Column(db.Boolean, default=False)
    message = db.Column(db.String(256))


class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    move = db.Column(db.String(15))  # 这里用 SAN 格式；当然可以接受 resign 和 draw
    moveuci = db.Column(db.String(15))  # 这里用 UCI 格式
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', uselist=False, backref='Record')
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'))
    round = db.relationship('Round', uselist=False, backref='Record')
    time = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board = db.Column(db.String(128))  # 这里用 FEN 存
    lastmove = db.Column(db.String(15))  # 这里用 UCI 格式；当然可以接受 resign 和 draw
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    game = db.relationship('Game', uselist=False, backref='Round')
    records = db.relationship('Record')

    def make_board(self):
        return chess.Board(self.board)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alive = db.Column(db.Boolean, default=True)
    rounds = db.relationship('Round')


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', uselist=False, backref='Application')
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    game = db.relationship('Game', uselist=False, backref='Application')
    color = db.Column(db.Boolean)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(256))
    time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'))
    application = db.relationship(
        'Application', uselist=False, backref='Message')
