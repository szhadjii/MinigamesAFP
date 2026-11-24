from flask import Blueprint, jsonify, request, g

from auth import admin_required
from models import User, db, GameSession, Score, Word, TypingText
from scores import GAMES

bp = Blueprint('admin', __name__, url_prefix='/admin')

# Felhasználók --------------------------------------------------------------------------

@bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    users = User.query.order_by(User.id).all()
    return jsonify([user.to_string() for user in users])

@bp.route('/users/<int:user_id>', methods=['PATCH'])
@admin_required
def update_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "Nincs ilyen felhasználó."}), 404
    data = request.get_json(silent=True) or {}

    if "role" in data and data["role"] not in ("admin", "player"):
        return jsonify({"error": "A szerepkör csak player vagy admin lehet."}), 400
    if "is_active" in data and not isinstance(data["is_active"], bool):
        return jsonify({"error": "Az is_active csak igaz vagy hamis lehet."}), 400

    if user.id == g.user.id:
        if data.get("role", "admin") != "admin" or data.get("is_active", True) is False:
            return jsonify({"error": "Saját magadat nem fokozhatod le és nem tilthatod le."}), 409

    if "role" in data:
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = data["is_active"]
    db.session.commit()
    return jsonify(user.to_string())

@bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "Nincs ilyen felhasználó."}), 404
    if user.id == g.user.id:
        return jsonify({"error": "Saját magadat nem törölheted"}), 409

    Score.query.filter_by(user_id=user_id).delete()
    GameSession.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Felhasználó törölve."})

# Pontszámok -----------------------------------------------------------------

@bp.route('/scores', methods=['GET'])
@admin_required
def list_scores():
    query = Score.query
    game = request.args.get('game')
    user_id = request.args.get('user_id', type=int)
    if game is not None:
        query = query.filter_by(game=game)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    results = []
    for score in query.order_by(Score.id.desc()).all():
        user = db.session.get(User, score.user_id)
        row = score.to_string()
        row["user_id"] = score.user_id
        row["username"] = user.username if user else None
        results.append(row)
    return jsonify(results)

@bp.route('/scores', methods=['DELETE'])
@admin_required
def delete_scores():
    score_id = request.args.get('score_id', type=int)
    game = request.args.get('game')
    if (score_id is None) and (game is None):
        return jsonify({"error": "Add meg az id vagy game paramétert (pontosan az egyiket)."}), 400

    if score_id is not None:
        score = db.session.get(Score, score_id)
        if score is None:
            return jsonify({"error": "Nincs ilyen eredmény."}), 404
        db.session.delete(score)
        db.session.commit()
        return jsonify({"deleted": True}), 200

    if game not in GAMES:
        return jsonify({"error": "Ismeretlen játék."}), 400
    deleted = Score.query.filter_by(game=game).delete()
    db.session.commit()
    return jsonify({"deleted": deleted}), 200


# Statisztika -------------------------------------------------------------------------------
@bp.route('/stats', methods=['GET'])
@admin_required
def get_stats():
    games = {}
    for game in GAMES:
        scores = Score.query.filter_by(game=game).all()
        points = [score.points for score in scores]
        games[game] = {
            "plays": GameSession.query.filter_by(game=game, status="finished").count(),
            "players": len({score.user_id for score in scores}),
            "avg_points": round(sum(points) / len(points), 1) if points else None,
            "best_points": max(points) if points else None,
        }

    return jsonify({"games": games, "users": {"total": User.query.count()}}), 200
