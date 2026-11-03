from flask import Blueprint, jsonify, request, g

from Backend.auth import admin_required
from Backend.models import User, db, GameSession, Score, Word, TypingText
from Backend.scores import GAMES

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
    query = Score.query.all()
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

# Stringek ----------------------------------------------------------------------------------------

def is_valid_word(text):
    return text.isalpha() and len(text) <= 30

def is_valid_text(text):
    return 10 <= len(text) <= 1000

CONTENT = {
    "words": (Word, is_valid_word, "A szó csak betűkből álljon (legfeljebb 30 karakter)."),
    "texts": (TypingText, is_valid_text, "A szöveg 10-1000 karakter legyen.")
}

def read_text(data, kind):
    text = data.get("text")
    if not isinstance(text, str):
        return None
    text = text.strip()
    is_valid = CONTENT[kind][1]
    if not is_valid(text):
        return None
    return text.lower() if kind == "words" else text

@bp.route('/<kind>', methods=['GET'])
@admin_required
def list_contents(kind):
    if kind not in CONTENT:
        return jsonify({"error": "Nincs ilyen végpont."}), 404
    model = CONTENT[kind][0]
    # noinspection unresolved-references
    return jsonify([item.to_string() for item in model.query.order_by(model.id).all()])

@bp.route('/<kind>', methods=['POST'])
@admin_required
def add_content(kind):
    if kind not in CONTENT:
        return jsonify({"error": "Nincs ilyen végpont."}), 404
    model = CONTENT[kind][0]
    message = CONTENT[kind][2]
    text = read_text(request.get_json(silent=True) or {}, kind)
    if text is None:
        return jsonify({"error": message}), 400
    item = model(text=text)
    db.session.add(item)
    db.session.commit()
    # noinspection unresolved-references
    return jsonify({item.to_string}), 201

@bp.route('/<kind>/<int:item_id>', methods=['PATCH'])
@admin_required
def update_content(kind, item_id):
    if kind not in CONTENT:
        return jsonify({"error": "Nincs ilyen végpont."}), 404
    model = CONTENT[kind][0]
    message = CONTENT[kind][2]
    item = db.session.get(model, item_id)
    if item is None:
        return jsonify({"error": "Nincs ilyen elem."}), 404
    data = request.get_json(silent=True) or {}
    if "text" in data:
        text = read_text(data, kind)
        if text is None:
            return jsonify({"error": message}), 400
        item.text = text
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            return jsonify({"error": "Az is_active értéke csak igaz/hamis lehet."}), 400
        item.is_active = data["is_active"]

    db.session.commit()
    return jsonify({item.to_string}), 200

@bp.route('/<kind>/<int:item_id>', methods=['DELETE'])
@admin_required
def delete_content(kind, item_id):
    if kind not in CONTENT:
        return jsonify({"error": "Nincs ilyen végpont."}), 404
    model = CONTENT[kind][0]
    item = db.session.get(model, item_id)
    if item is None:
        return jsonify({"error": "Nincs ilyen elem."}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Nincs ilyen elem."}), 200

# Statisztika -------------------------------------------------------------------------------





