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
    try:
        move = get_round_now().make_board().parse_san(move)
    except ValueError:
        return "-1"
    return "1"


@app.route("/")
def main():
    return "game:{}\n round:{}".format(get_game_now().id, get_round_now().id)
