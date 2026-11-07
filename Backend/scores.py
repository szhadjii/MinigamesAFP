from flask import Blueprint, request, jsonify, g

from auth import login_required
from models import User, Score, db

bp = Blueprint('scores', __name__, url_prefix='/scores')
GAMES = "tictactoe"
SUMPOINT_GAMES = "tictactoe"

def save_score(user_id, game, points, difficulty=None, details=None, commit=True):
    score = Score(user_id=user_id, game=game, points=points, difficulty=difficulty, details=details)
    db.session.add(score)
    if commit:
        db.session.commit()
    return score

def top_score(game, difficulty=None, limit=3):
    query = Score.query.filter_by(game=game)
    if difficulty is not None:
        query = query.filter_by(difficulty=difficulty)

    points_by_user = {}
    for score in query.all():
        points_by_user.setdefault(score.user_id, []).append(score.points)
    results = []
    for user_id, points in points_by_user.items():
        user = db.session.get(User, user_id)
        if user is None:
            continue
        total = sum(points) if game in SUMPOINT_GAMES else max(points)
        if total > 0:
            results.append({"username": user.username, "points": total})

    results.sort(key=lambda row: (-row["points"], row["username"]))
    return results[:limit]

@bp.route("/top", methods=["GET"])
@login_required
def top():
    game = request.args.get("game")
    difficulty = request.args.get("difficulty")
    if game not in GAMES:
        return jsonify({"error": "Ismeretlen játék."}), 400
    return jsonify(top_score(game, difficulty=difficulty))

@bp.route("/me", methods=["GET"])
@login_required
def my_score():
    query = Score.query.filter_by(user_id=g.user.id)
    game = request.args.get("game")
    if game:
        query = query.filter_by(game=game)
    rows = query.order_by(Score.id.desc()).all()
    return jsonify([row.to_dict() for row in rows])

