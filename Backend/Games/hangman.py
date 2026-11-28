from flask import Blueprint, request, jsonify
import uuid
import sys
import os

# Hogy elérjük a szülő mappában lévő content_pool.py-t:
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from content_pool import pick_hangman_word

bp = Blueprint('hangman', __name__)

# Játékállapotok memóriában
hangman_sessions = {}

@bp.route("/api/hangman/start", methods=["POST"])
def start_game():
    difficulty = request.args.get("difficulty", "medium")

    # A content_pool-ból kérjük a szót (ez hívja az LLM-et vagy a fallbacket)
    word = pick_hangman_word(difficulty=difficulty)

    if not word:
        return jsonify({"error": "Nincs elérhető szó a készletben."}), 503

    session_id = str(uuid.uuid4())

    # Játékállapot inicializálása
    hangman_sessions[session_id] = {
        "word": word.upper(),
        "guessed": [],
        "mistakes": 0,
        "max_mistakes": 6,
        "finished": False,
        "won": False
    }

    # Visszaküldjük a hosszt, de a szót NEM!
    return jsonify({
        "sessionId": session_id,
        "wordLength": len(word),
        "maxMistakes": 6,
        "hint": "Találd ki a szót!"
    })


@bp.route("/api/hangman/guess", methods=["POST"])
def guess_letter():
    session_id = request.args.get("sessionId")
    letter = request.args.get("letter", "").upper()

    if not session_id or session_id not in hangman_sessions:
        return jsonify({"error": "Nincs ilyen játék."}), 404

    state = hangman_sessions[session_id]

    if state["finished"]:
        return jsonify({"error": "A játék már véget ért."}), 400

    if letter in state["guessed"]:
        return jsonify({"message": "Ezt a betűt már tippelted."})

    state["guessed"].append(letter)
    correct = letter in state["word"]

    if not correct:
        state["mistakes"] += 1

    # Győzelem ellenőrzése
    all_found = all(c in state["guessed"] for c in state["word"] if c != ' ')
    if all_found:
        state["finished"] = True
        state["won"] = True
    elif state["mistakes"] >= state["max_mistakes"]:
        state["finished"] = True
        state["won"] = False

    display = "".join(c if c in state["guessed"] or c == ' ' else "_" for c in state["word"])

    return jsonify({
        "display": display,
        "mistakes": state["mistakes"],
        "maxMistakes": state["max_mistakes"],
        "finished": state["finished"],
        "won": state["won"],
        "message": "Helyes tipp!" if correct else "Hibás tipp!"
    })
