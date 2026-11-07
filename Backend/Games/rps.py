import random

from flask import Blueprint, jsonify, request, g

import game_sessions
from auth import login_required
from models import GameSession, db

bp = Blueprint('rps', __name__, url_prefix='/rps')

GAME = "rps"
ROUNDS = 5
POINTS_WIN = 10
POINTS_DRAW = 3
MOVES = ("rock", "paper", "scissors")                       # kő, papír, olló
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}  # kulcs legyőzi az értéket


def public_state(state):
    return {"round": state["round"], "total": ROUNDS,
            "score": state["points"], "history": state["history"]}


@bp.route('/start', methods=['POST'])
@login_required
def start():
    GameSession.abandon_active(g.user.id, GAME)
    db.session.commit()
    state = {"round": 0, "points": 0, "history": []}
    game_sessions.start(g.user.id, GAME, state)
    return jsonify(public_state(state)), 201


@bp.route('/current', methods=['GET'])
@login_required
def current():
    session = game_sessions.get_active(g.user.id, GAME)
    if session is None:
        return jsonify({"error": "Nincs folyamatban lévő meccs."}), 404
    return jsonify(public_state(session.state))


@bp.route('/play', methods=['POST'])
@login_required
def play():
    session = game_sessions.get_active(g.user.id, GAME)
    if session is None:
        return jsonify({"error": "Nincs folyamatban lévő meccs."}), 404

    move = (request.get_json(silent=True) or {}).get("move")
    if move not in MOVES:
        return jsonify({"error": "A move értéke rock, paper vagy scissors lehet."}), 400

    computer = random.choice(MOVES)
    if move == computer:
        outcome, gained = "draw", POINTS_DRAW
    elif BEATS[move] == computer:
        outcome, gained = "win", POINTS_WIN
    else:
        outcome, gained = "loss", 0

    state = dict(session.state)
    state["round"] += 1
    state["points"] += gained
    state["history"] = state["history"] + [{"player": move, "computer": computer, "outcome": outcome}]

    response = {"player": move, "computer": computer, "outcome": outcome,
                "gained": gained, "round": state["round"], "total": ROUNDS, "score": state["points"]}

    if state["round"] >= ROUNDS:
        counts = {k: sum(1 for h in state["history"] if h["outcome"] == k) for k in ("win", "draw", "loss")}
        game_sessions.finish(session, state, points=state["points"], details=counts)
        response.update(finished=True, points=state["points"], **{"stats": counts})
    else:
        game_sessions.save_state(session, state)
        response["finished"] = False
    return jsonify(response)
