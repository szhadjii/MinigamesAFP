import random
import time
from datetime import timezone, datetime

from flask import Blueprint, request, jsonify, g

import game_sessions
from auth import login_required
from models import db, TypingText, GameSession

GAME_ID = "typing"
MODES = ("bot", "practice")
BOT_WPM = {"slow": 25, "medium": 45, "fast": 70}
BOT_VARIATION = 0.1
MAX_WPM = 250


def current_time():
    return time.time()

def choose_bot_wpm(difficulty):
    base = BOT_WPM[difficulty]
    return round(base * random.uniform(1- BOT_VARIATION, 1 + BOT_VARIATION,), 1)

def calculate_wpm(characters, seconds):
    return (characters / 5) / (seconds / 60)

def calculate_accuracy(text, typed):
    correct = 0
    for i in range(len(text)):
        if i < len(typed) and typed[i] == text[i]:
            correct += 1
    return correct / len(text)

def bot_finish_in_sec(characters, bot_wpm):
    return (characters / 5) / bot_wpm * 60

def abandon_round(session):
    session.status = "abandoned"
    session.finished_at = datetime.now(timezone.utc)
    db.session.commit()


bp = Blueprint("typing", __name__, url_prefix="/typing")

@bp.route('/start', methods=['POST'])
@login_required
def start():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "bot")
    difficulty = data.get("difficulty", "medium")
    if mode not in MODES:
        return jsonify({"error": "Érvénytelen kérés."}), 400
    if mode == "bot" and difficulty not in BOT_WPM:
        return jsonify({"error": "Érvénytelen kérés."}), 400

    texts = TypingText.query.filter_by(is_active=True).all()
    if not texts:
        return jsonify({"error": "Jelenleg nincs elérhető tartalom."}), 503
    chosen_text = random.choice(texts)

    bot_wpm = choose_bot_wpm(difficulty) if mode == "bot" else None
    state = {
        "mode": mode,
        "difficulty": difficulty,
        "text": chosen_text,
        "started_at": current_time(),
        "bot_wpm": bot_wpm,
    }
    session = game_sessions.start(g.user.id, GAME_ID, state)

    body = {"session_id": session.id, "text": chosen_text.text}
    if mode == "bot":
        body["bot_wpm"] = bot_wpm
    return jsonify(body)

@bp.route('/finish', methods=['POST'])
@login_required
def finish():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    typed = data.get("typed_text")
    if not isinstance(session_id, int) or isinstance(session_id, bool) or not isinstance(typed, str):
        return jsonify({"error": "Érvénytelen kérés."}), 400

    session = db.session.get(GameSession, session_id)
    if session is None or session.user_id != g.user.id or session.game != GAME_ID:
        return jsonify({"error": "Nincs folyamatban lévő játék."}), 404
    if session.status != "active":
        return jsonify({"error": "A játék véget ért. Indíts új játékot."}), 409

    state = session.state
    text = state["text"]
    if len(typed) < len(text) or len(typed) > 2 * len(text):
        return jsonify({"error": "Érvénytelen kérés."}), 400

    elapsed = current_time() - state["started_at"]
    if elapsed <= 0 or calculate_wpm(len(typed), elapsed) > MAX_WPM:
        abandon_round(session)
        return jsonify({"error": "Az eredmény érvénytelen, a kör nem számít."}), 400

    wpm = calculate_wpm(len(text), elapsed)
    accuracy = calculate_accuracy(text, typed)
    points = round(wpm * accuracy)

    result = {
        "elapsed_seconds": round(elapsed, 2),
        "accuracy": round(accuracy, 3),
        "wpm": round(wpm, 1),
        "points": points,
    }
    details = {
        "mode": state["mode"],
        "wpm": result["wpm"],
        "accuracy": result["accuracy"],
        "elapsed_seconds": result["elapsed_seconds"],
    }

    if state["mode"] == "bot":
        bot_seconds = bot_finish_in_sec(len(text), state["bot_wpm"])
        winner = "player" if elapsed < bot_seconds else "bot"
        result["winner"] = winner
        details["winner"] = winner
        details["bot_wpm"] = state["bot_wpm"]

    final_state = dict(state)
    final_state["result"] = result
    game_sessions.finish(session, final_state, points, state["difficulty"], details=details)
    return jsonify(result)