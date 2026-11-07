import functools

from flask import Blueprint, session, jsonify, request, g
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

from models import User, db, GameSession

bp = Blueprint('auth', __name__, url_prefix='/auth')

def current_user():
    user_id = session.get('user_id')
    if user_id is None:
        return None
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        session.clear()
        return None
    return user

def find_user(username):
    return User.query.filter(func.lower(User.username) == username.lower()).first()

def login_required(view):
    @functools.wraps(view)
    def wrap(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify({"error": "Nem vagy bejelentkezve. Kérlek jelentkezz be a folytatáshoz."}), 401
        g.user = user
        return view(*args, **kwargs)
    return wrap

def admin_required(view):
    @login_required
    @functools.wraps(view)
    def wrap(*args, **kwargs):
        if g.user.role != 'admin':
            return jsonify({"error": "Admin jogosultság szükséges!"}), 401
        return view(*args, **kwargs)
    return wrap

def read_credentials():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')
    if not isinstance(username, str) or not isinstance(password, str):
        return None, None
    return username, password

@bp.route('/register', methods=['POST'])
def register():
    username, password = read_credentials()
    if username is None or not (3 <= len(username) <= 20):
        return jsonify({"error": "A felhasználónév 3 és 20 karakter között legyen."}), 400
    if password == "" or len(password) < 8:
        return jsonify({"error": "A jelszó legalább 8 karakter legyen."}), 400
    if find_user(username) is not None:
        return jsonify({"error": "Ez a felhasználónév már foglalt."}), 409

    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({"id": user.id, "username": user.username}), 201

@bp.route('/login', methods=['POST'])
def login():
    username, password = read_credentials()
    user = find_user(username) if username else None
    if user is None or not password or not check_password_hash(pwhash=user.password_hash, password=password):
        return jsonify({"error": "Hibás felhasználónév vagy jelszó."}), 401
    if not user.is_active:
        return jsonify({"error": "A fiókod le van tiltva."}), 403

    session.clear()
    session["user_id"] = user.id
    return jsonify(user.to_string())

@bp.route('/logout', methods=['POST'])
def logout():
    user = current_user()
    if user is not None:
        GameSession.abandon_active(user.id)
        db.session.commit()
    session.clear()
    return jsonify({"message": "Sikeresen kijelentkeztél."})

@bp.route('/me', methods=['GET'])
@login_required
def me():
    return jsonify(g.user.to_string())