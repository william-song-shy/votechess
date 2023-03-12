import re
from flask import Flask, request, render_template, jsonify, flash, redirect, url_for
from db import *
from tools import *
from sqlalchemy.sql import text
from sqlalchemy import func, desc
from flask_migrate import Migrate
from wtforms import SubmitField, StringField, PasswordField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import chess.pgn
from sys import platform

DEV = platform == "win32"

app = Flask(__name__)

app.secret_key = environ.get('sk')

DIALECT = 'mysql'
DRIVER = 'pymysql'
USERNAME = 'votechess'
PASSWORD = environ.get('mysqlpassword')
HOST = '127.0.0.1'
PORT = '3306'
DATABASE = 'votechess'

app.config['SQLALCHEMY_DATABASE_URI'] = "{}+{}://{}:{}@{}:{}/{}?charset=utf8".format(
    DIALECT, DRIVER, USERNAME, PASSWORD, HOST, PORT, DATABASE)
if DEV:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.root_path + '/data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return user


def p_info(mes):
    app.logger.info(mes)


def p_warning(mes):
    app.logger.warning(mes)


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
    get_game_now()
    return Round.query.order_by(text("-id")).first()


@app.route("/api/board")
def api_board():
    board = chess.Board(get_round_now().board)
    return jsonify({"FEN": board.fen(), "turn": "WHITE" if board.turn else "BLACK"})


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


@app.route("/api/apply", methods=['POST'])
def api_apply():
    color = request.form.get("color")
    if not color in ('0', '1'):
        return {"status": "error", "message": "WTF color"}
    else:
        color=int(color)
    if not current_user.is_authenticated:
        return {"status": "error", "message": "You are not logged in"}
    if not current_user.allowed:
        return {"status": "error", "message": "You are not allowed to play"}
    application = Application.query.filter(
        Application.game_id == get_game_now().id, Application.user_id == current_user.id).first()
    if not application:
        application = Application(user=current_user, game=get_game_now(), color=color)
        db.session.add(application)
    else:
        return {"status": "error", "message": "You can't change your color"}
        application.color = color
    db.session.commit()
    return {"status": "success"}


@app.route("/api/applied")
def api_applied():
    if not current_user.is_authenticated:
        return {"status": "error", "message": "You are not logged in"}
    if not current_user.allowed:
        return {"status": "error", "message": "You are not allowed to play"}
    application = Application.query.filter(
        Application.game_id == get_game_now().id, Application.user_id == current_user.id).first()
    if not application:
        return jsonify({"result": -1})
    else:
        return jsonify({"message": int(application.color)})


@app.route("/api/vote",methods=['POST'])
def api_vote():
    move = request.form.get("move")
    if not current_user.is_authenticated:
        return {"status": "error", "message": "You are not logged in"}
    if not current_user.allowed:
        return {"status": "error", "message": "You are not allowed to play"}
    application = Application.query.filter(
        Application.game_id == get_game_now().id, Application.user_id == current_user.id).first()
    if not application:
        return {"status": "error", "message": "You didn't sign up"}
    if application.color != get_round_now().make_board().turn:
        return {"status": "error", "message": "It's not your turn"}
    if move != "resign":
        try:
            movet = get_round_now().make_board().parse_san(move)
        except ValueError:
            return {"status": "error", "message": "Illegal move"}
    record = Record.query.filter(
        Record.user_id == current_user.id, Record.round_id == get_round_now().id).first()
    if record:
        record.move = move
        record.moveuci = movet.uci() if move != "resign" else "resign"
        record.time = datetime.datetime.utcnow()
    else:
        record = Record(move=move, user=current_user, round=get_round_now(
        ), moveuci=movet.uci() if move != "resign" else "resign")
        db.session.add(record)
    db.session.commit()
    return {"status": "success"}


def game_end(data):
    send_text("Game ended! {}".format(data[1]))
    game = get_game_now()
    rounds = game.rounds
    pgngame = chess.pgn.Game()
    lstnode = pgngame
    for i in rounds:
        if i.lastmove is not None and i.lastmove != "resign" and i.lastmove != "draw":
            move = chess.Move.from_uci(i.lastmove)
            lstnode = lstnode.add_variation(move)
    if not data[3] == "resign":
        lstnode = lstnode.add_variation(data[3])
    else:
        lstnode.comment = "{} resigned after that".format(
            "White" if data[2] == "1-0" else "Black")
    pgngame.headers["Event"] = "VoteChess #{}".format(game.id)
    pgngame.headers["Site"] = "http://votechess.rotriw.com/"
    pgngame.headers["Result"] = data[1]
    url = upload_to_lichess(pgngame)
    send_text("You can see this round {}".format(url))
    pass  # 先不写


@app.route("/api/count")
def api_count():
    password = request.args.get("password")
    if password != environ.get("superadminpassword"):
        return {"status": "error", "message": "You have no permition"}
    records = Record.query.with_entities(func.max(Record.time).label("maxtime"), Record.move, Record.moveuci,
                                         func.count().label(
                                             "count")).filter(Record.round_id == get_round_now().id).group_by(
        Record.moveuci).order_by(desc(func.count()), text("maxtime"))
    if records.count() == 0:
        send_text("Skipped. No one voted in this round.")
        return "-1"
    new_board = get_round_now().make_board()
    rf = records.first()
    if rf.move == "resign":
        gen_and_send_board_pic(new_board)
        send_text("{} is chosen with {} vote{}".format(
            rf.move, rf.count, "s" if rf.count > 1 else ""))
        game_end((None, "1-0" if not new_board.turn else "0-1", None, "resign"))
        get_game_now().alive = False
        game = Game()
        db.session.add(game)
        round = Round()
        round.board = chess.Board().fen()
        db.session.add(round)
        game.rounds.append(round)
        db.session.commit()
        return str(records.count())
    new_board.push_san(rf.move)
    if is_it_end(new_board):
        gen_and_send_board_pic(new_board)
        send_text("{} is chosen with {} vote{}".format(
            rf.move, rf.count, "s" if rf.count > 1 else ""))
        game_end(is_it_end(new_board))
        get_game_now().alive = False
        game = Game()
        db.session.add(game)
        round = Round()
        round.board = chess.Board().fen()
        db.session.add(round)
        game.rounds.append(round)
        db.session.commit()
        return str(records.count())
    new_round = Round(board=new_board.fen(),
                      game=get_game_now(), lastmove=rf.moveuci)
    db.session.add(new_round)
    db.session.commit()
    gen_and_send_board_pic(new_board)
    send_text("{} is chosen with {} vote{}".format(
        rf.move, rf.count, ("s" if rf.count > 1 else "")))
    return str(records.count())


@app.route("/api/current")
def api_current():
    game = get_game_now()
    round = get_round_now()
    applications = Application.query.filter(
        Application.game_id == game.id, Application.color == int(round.make_board().turn)).all()
    # p_info(game.id)
    # p_info(round.make_board().turn)
    users = [i.user for i in applications]
    records = round.records
    res = {}
    for i in records:
        res[i.user.username] = i.move
    for i in users:
        if res.get(i.username):
            continue
        else:
            res[i.username] = None
    return jsonify(res)


@app.route("/api/message")
def api_message():
    lastid = request.args.get("lastid", type=int, default=1e10)
    if not current_user.is_authenticated:
        return {"status": "error", "message": "You are not logged in"}
    if not current_user.allowed:
        return {"status": "error", "message": "You are not allowed to send message"}
    game = get_game_now()
    application = Application.query.filter(
        Application.user_id == current_user.id, Application.game_id == game.id).first()
    if not application:
        return {"status": "error", "message": "You are not in this game"}
    messages = Message.query.join(Message.application, Application.game, Application.user).filter(
        Game.id == game.id, Application.color == application.color).filter(Message.id < lastid).order_by(Message.id.desc()).limit(10)
    # p_info(messages)
    return jsonify(
        [{"id": i.id, "content": i.content, "time": i.time, "username": i.application.user.username} for i in messages.all()])


@app.route("/api/send", methods=["POST"])
def api_send():
    content = request.form.get("content")
    if not current_user.is_authenticated:
        return {"status": "error", "message": "You are not logged in"}
    if not current_user.allowed:
        return {"status": "error", "message": "You are not allowed to send message"}
    game = get_game_now()
    application = Application.query.filter(
        Application.user_id == current_user.id, Application.game_id == game.id).first()
    if not application:
        return {"status": "error", "message": "You are not in this game"}
    message = Message(content=content, application=application)
    db.session.add(message)
    db.session.commit()
    return {"status": "success"}


@app.route("/")
def main():
    show_apply = False
    if current_user.is_authenticated:
        application = Application.query.filter(
            Application.game_id == get_game_now().id, Application.user_id == current_user.id).first()
        if not application:
            show_apply = True
    return render_template("main.html", show_apply=show_apply)
    return "game:{}\n round:{}".format(get_game_now().id, get_round_now().id)


@app.route("/account/apply", methods=["GET", "POST"])
def account_apply():
    class ApplyForm(FlaskForm):
        username = StringField("Username", validators=[DataRequired()])
        password = PasswordField("Password", validators=[DataRequired()])
        message = StringField("Message", validators=[DataRequired()])
        submit = SubmitField("Submit")

    form = ApplyForm()
    if form.validate_on_submit():
        user = User.query.filter(User.username == form.username.data).first()
        if user:
            flash("Username already exists", category="error")
            return redirect(url_for("main"))
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        application = AccountApplication(user=user, message=form.message.data)
        db.session.add(application)
        db.session.commit()
        flash("Application submitted.Please wait for the administrator to review.", category="success")
        return redirect(url_for("main"))
    return render_template("account_apply.html", form=form)


@app.route("/account/login", methods=["GET", "POST"])
def account_login():
    if current_user.is_authenticated:
        flash("You are already logged in", category="error")
        return redirect(url_for("main"))

    class LoginForm(FlaskForm):
        username = StringField("Username", validators=[DataRequired()])
        password = PasswordField("Password", validators=[DataRequired()])
        submit = SubmitField("Submit")

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(User.username == form.username.data).first()
        if user and user.validate_password(form.password.data):
            login_user(user)
            flash("Login successfully", category="success")
            return redirect(url_for("main"))
        else:
            flash("Username or password is wrong", category="error")
            return redirect(url_for("main"))
    return render_template("account_login.html", form=form)


@app.route("/account/logout")
def account_logout():
    if not current_user.is_authenticated:
        flash("You are not logged in", category="error")
        return redirect(url_for("main"))
    logout_user()
    flash("Logout successfully", category="success")
    return redirect(url_for("main"))
