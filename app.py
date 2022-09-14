import re
from flask import Flask, request
from os import environ, path
from dotenv import load_dotenv
from db import *
from tools import *
from sqlalchemy.sql import text
from sqlalchemy import func


basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))


app = Flask(__name__)


DIALECT = 'mysql'
DRIVER = 'pymysql'
USERNAME = 'songhongyi'
PASSWORD = environ.get('mysqlpassword')
HOST = '127.0.0.1'
PORT = '3306'
DATABASE = 'votechess'


# app.config['SQLALCHEMY_DATABASE_URI'] = "{}+{}://{}:{}@{}:{}/{}?charset=utf8".format(
#    DIALECT, DRIVER, USERNAME, PASSWORD, HOST, PORT, DATABASE)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+app.root_path+'/data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def get_game_now():
    if not Game.query.first():
        game = Game()
        db.session.add(game)
        round = Round()
        round.board = chess.Board().fen()
        db.session.add(round)
        game.rounds.append(round)
        db.session.commit()
    return Game.query.order_by(text("-id")).first()


def get_round_now():
    return Round.query.order_by(text("-id")).first()


@app.route("/api/legal")
def api_legal():
    move = request.args.get("move")
    if move == "resign" or move == "draw":
        return "1"
    try:
        move = get_round_now().make_board().parse_san(move)
    except ValueError:
        return "-1"
    return "1"


@app.route("/api/apply")
def api_apply():
    username = request.args.get("username")
    password = request.args.get("password")
    color = request.args.get("color", type=int)
    if not color in (0, 1):
        return {"status": "error", "message": "WTF color"}
    user = User.query.filter(User.username == username).first()
    if not user:
        return {"status": "error", "message": "Wrong username"}
    if not user.validate_password(password):
        return {"status": "error", "message": "Wrong password"}
    application = Application.query.filter(
        Application.game_id == get_game_now().id, Application.user_id == user.id).first()
    if not application:
        application = Application(user=user, game=get_game_now(), color=color)
        db.session.add(application)
    else:
        return {"status": "error", "message": "You can't change your color"}
        application.color = color
    db.session.commit()
    return {"status": "success"}


@app.route("/api/vote")
def api_vote():
    move = request.args.get("move")
    username = request.args.get("username")
    password = request.args.get("password")
    user = User.query.filter(User.username == username).first()
    if not user:
        return {"status": "error", "message": "Wrong username"}
    if not user.validate_password(password):
        return {"status": "error", "message": "Wrong password"}
    application = Application.query.filter(
        Application.game_id == get_game_now().id, Application.user_id == user.id).first()
    if not application:
        return {"status": "error", "message": "You didn't sign up"}
    if application.color != get_round_now().make_board().turn:
        return {"status": "error", "message": "It's not your turn"}
    try:
        movet = get_round_now().make_board().parse_san(move)
    except ValueError:
        return {"status": "error", "message": "Illegam move"}
    record = Record.query.filter(
        Record.user_id == user.id, Record.round_id == get_round_now().id).first()
    if record:
        record.move = move
    else:
        record = Record(move=move, user=user, round=get_round_now())
        db.session.add(record)
    db.session.commit()
    return {"status": "success"}


@app.route("/api/count")
def api_count():
    password = request.args.get("password")
    if password != environ.get("superadminpassword"):
        return {"status": "error", "message": "You have no permition"}
    records = Record.query.with_entities(func.min(Record.time).label("mintime"), Record.move, func.count().label(
        "count")).filter(Record.round_id == get_round_now().id).group_by(Record.move).order_by(text("-count"), text("mintime"))
    new_board = get_round_now().make_board()
    new_board.push_san(records.first().move)
    new_round = Round(board=new_board.fen(), game=get_game_now())
    db.session.add(new_round)
    db.session.commit()
    gen_and_send_board_pic(new_board)
    send_text("{} is chosen with {} votes".format(records.first().move,records.first().count))
    return str(records.count())


@app.route("/")
def main():
    return "game:{}\n round:{}".format(get_game_now().id, get_round_now().id)
