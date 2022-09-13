# 是时候考虑模块化一些了/cy

import chess
import cairosvg
import base64
import hashlib
import requests

webhook = "damnitidon'thave"


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
    if len(board.move_stack >= 1):
        pic = chess.svg.board(board, lastmove=board.peek())
    else:
        pic = chess.svg.board(board)
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
    return chess.Move(s+t)


def judge_legal_move(board, move):
    return move in board.legal_moves


def is_it_end(board):
    if not board.Outcome():
        return None
    else:
        return (board.Outcome().termination, board.Outcome().result, board.Outcome().winner)
