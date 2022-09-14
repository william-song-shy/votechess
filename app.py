import re
from flask import Flask, request
from os import environ, path
from dotenv import load_dotenv
from db import *
from tools import *
from sqlalchemy.sql import text


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

@app.route ("/api/vote")
def api_vote():
    move = request.args.get("move")
    username=request.args.get("username")
    password=request.args.get("password")
    user=User.query.filter(User.username==username).first()
    if not user:
        return {"status":"error","message":"Wrong username"}
    if not user.validate_password(password):
        return {"status":"error","message":"Wrong password"}
    application = Application.query.filter(Application.game_id==get_game_now().id,Application.user_id==user.id).first()
    if not application:
        return {"status":"error","message":"You didn't sign up"}
    if application.color != get_round_now().make_board().turn:
        return {"status":"error","message":"It's not your turn"}
    try:
        movet = get_round_now().make_board().parse_san(move)
    except ValueError:
        return {"status":"error","message":"Illegam move"}
    record=Record.query.filter(Record.user_id==user.id,Record.round_id==get_round_now().id).first()
    if record:
        record.move=move
    else:
        record=Record(move=move,user=user,round=get_round_now())
        db.session.add(record)
    db.session.commit()
    return {"status":"success"}


@app.route("/")
def main():
    return "game:{}\n round:{}".format(get_game_now().id, get_round_now().id)
