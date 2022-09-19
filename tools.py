# 是时候考虑模块化一些了/cy

import chess
import chess.svg
import cairosvg
import base64
import hashlib
import requests
from os import environ, path
from dotenv import load_dotenv

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))

webhook = environ.get("webhook")


def p_info(mes):
    print(mes)  # 写了日志再改


def send_text(mes, at=[]):
    """往群里发一条消息"""
    data = {"msgtype": "text", "text": {
        "content": mes, "mentioned_list": at}}
    r = requests.post(webhook, json=data)
    p_info(r.text)


def gen_and_send_board_pic(board):
    """将 board 发到群里"""
    if len(board.move_stack) >= 1:
        pic = chess.svg.board(board, lastmove=board.peek())
    else:
        pic = chess.svg.board(board)
    pic = cairosvg.svg2png(pic)
    b64 = base64.b64encode(pic)
    md5 = hashlib.md5()
    md5.update(pic)
    digest = md5.hexdigest()
    data = {"msgtype": "image", "image": {
        "base64": b64.decode("utf-8"), "md5": digest}}
    r = requests.post(webhook, json=data)
    p_info(r.text)


def gen_move(s, t):
    """用前端的返回生成 chess.Move"""
    return chess.Move.from_uci(s+t)


def judge_legal_move(board, move):
    return move in board.legal_moves


def is_it_end(board):
    if not board.outcome():
        return None
    else:
        return (board.outcome().termination, board.outcome().result(), board.outcome().winner)


if __name__ == "__main__":
    print(gen_move("e2", "e4"))
    board = chess.Board()
    print(judge_legal_move(board, gen_move("e2", "e4")))
    print(is_it_end(board))
    board = chess.Board(
        "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
    print(is_it_end(board))
