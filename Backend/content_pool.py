"""
content_pool.py

Glue between content_generator.py (LLM) and the existing database tables.

The games never call the LLM directly. They ask this module for content, which
is served from the DB (typing_texts, words, quiz_questions). When a player is
running low on content they have not seen yet, the pool is topped up with newly
generated items in a background thread, so game start stays fast.

  * typing texts -> TypingText (existing table)
  * hangman words -> Word (existing `words` table; difficulty = word length)
  * quiz questions -> QuizQuestion (new table, see the model snippet in the README)

"Seen" content is read from game_sessions: the game must store the id(s) of the
content in its session state:
    typing  -> state["text_id"]       (already the case)
    hangman -> state["word_id"]
    quiz    -> state["question_ids"]  (list)

Config flags (Flask app.config):
    CONTENT_AUTO_REFILL        default True. False: never generate (tests, demos).
    CONTENT_BACKGROUND_REFILL  default True. False: top-up runs synchronously (tests).
"""

from __future__ import annotations

import logging
import random
import threading
import time
from functools import partial
from typing import Any, Callable, Iterable, List, Optional, Set

from flask import current_app

import models
from content_generator import (
    DIFFICULTIES,
    HANGMAN_LENGTHS,
    generate_hangman_words,
    generate_quiz,
    generate_typing_texts,
)
from models import GameSession, TypingText, db

logger = logging.getLogger(__name__)

# When a player has fewer unseen items than this, a top-up is started.
LOW_WATERMARK = {"typing": 3, "hangman": 8, "quiz": 10}
# How many items one top-up asks for.
BATCH = {"typing": 5, "hangman": 15, "quiz": 10}
# Minimum seconds between two top-up attempts of the same kind (protects the API quota
# when the LLM is down or the fallback content is exhausted).
REFILL_COOLDOWN = 60
# How many of the player's latest sessions count as "already seen".
RECENT_SESSIONS = 100

QUIZ_TOPICS = [
    "általános műveltség", "földrajz", "történelem", "természettudomány",
    "irodalom", "sport", "technika és informatika", "zene és filmek",
]

_lock = threading.Lock()
_running: Set[str] = set()
_last_attempt: dict = {}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _model(name: str):
    """Look up a model lazily so a missing optional model only breaks its own game."""
    try:
        return getattr(models, name)
    except AttributeError as exc:
        raise RuntimeError(f"models.{name} is missing - see the README of the content pool") from exc


def _key(text: str) -> str:
    return " ".join(text.split()).casefold()


def _recent_values(user_id: int, game: str, state_key: str) -> Set[Any]:
    rows = (
        GameSession.query.filter_by(user_id=user_id, game=game)
        .order_by(GameSession.id.desc())
        .limit(RECENT_SESSIONS)
        .all()
    )
    values: Set[Any] = set()
    for row in rows:
        state = row.state if isinstance(row.state, dict) else {}
        value = state.get(state_key)
        if isinstance(value, list):
            values.update(value)
        elif value is not None:
            values.add(value)
    return values


def _refill(kind: str, job: Callable[[], None], force: bool = False) -> None:
    """
    Run `job` (inserts new items into the DB).
      force=True : run now, in this request (the pool is empty, we have to wait).
      otherwise  : background thread, at most one per kind, with a cooldown.
    """
    app = current_app._get_current_object()
    if not app.config.get("CONTENT_AUTO_REFILL", True):
        return

    def run() -> None:
        try:
            job()
        except Exception:  # noqa: BLE001 - a failed top-up must never break a game
            logger.exception("Content top-up failed (%s)", kind)
            db.session.rollback()

    if force:
        run()
        return

    now = time.time()
    with _lock:
        if kind in _running or now - _last_attempt.get(kind, 0) < REFILL_COOLDOWN:
            return
        _running.add(kind)
        _last_attempt[kind] = now

    def worker() -> None:
        try:
            with app.app_context():
                run()
        finally:
            with _lock:
                _running.discard(kind)

    if app.config.get("CONTENT_BACKGROUND_REFILL", True):
        threading.Thread(target=worker, daemon=True).start()
    else:
        worker()


def _add_texts(model, texts: Iterable[str], existing_keys: Set[str]) -> int:
    added = 0
    for text in texts:
        k = _key(text)
        if k in existing_keys:
            continue
        existing_keys.add(k)
        db.session.add(model(text=text, is_active=True))
        added += 1
    db.session.commit()
    logger.info("Content top-up (%s): %d new items", model.__name__, added)
    return added


# --------------------------------------------------------------------------- #
# Typing game
# --------------------------------------------------------------------------- #


def _typing_job() -> None:
    existing = [t.text for t in TypingText.query.all()]
    result = generate_typing_texts(
        difficulty=random.choice(DIFFICULTIES), count=BATCH["typing"], exclude=existing
    )
    _add_texts(TypingText, result.items, {_key(t) for t in existing})


def pick_typing_text(user_id: int) -> Optional[TypingText]:
    """A random active text the player has not played recently (None if there is none)."""
    active = TypingText.query.filter_by(is_active=True).all()
    if not active:
        _refill("typing", _typing_job, force=True)
        active = TypingText.query.filter_by(is_active=True).all()

    seen = _recent_values(user_id, "typing", "text_id")
    unseen = [t for t in active if t.id not in seen]
    if len(unseen) < LOW_WATERMARK["typing"]:
        _refill("typing", _typing_job)

    candidates = unseen or active
    return random.choice(candidates) if candidates else None


# --------------------------------------------------------------------------- #
# Hangman (the `words` table has no difficulty column: difficulty = word length)
# --------------------------------------------------------------------------- #


def _words_job(difficulty: str) -> None:
    Word = _model("Word")
    existing = [w.text for w in Word.query.all()]
    result = generate_hangman_words(difficulty=difficulty, count=BATCH["hangman"], exclude=existing)
    _add_texts(Word, result.items, {_key(w) for w in existing})


def pick_hangman_word(user_id: int, difficulty: str):
    """A random active word of the right length that the player has not seen recently."""
    if difficulty not in HANGMAN_LENGTHS:
        raise ValueError(f"difficulty must be one of {tuple(HANGMAN_LENGTHS)}")
    Word = _model("Word")
    low, high = HANGMAN_LENGTHS[difficulty]
    job = partial(_words_job, difficulty)
    kind = f"hangman-{difficulty}"

    def active_words() -> List[Any]:
        return [w for w in Word.query.filter_by(is_active=True).all() if low <= len(w.text) <= high]

    active = active_words()
    if not active:
        _refill(kind, job, force=True)
        active = active_words()

    seen = _recent_values(user_id, "hangman", "word_id")
    unseen = [w for w in active if w.id not in seen]
    if len(unseen) < LOW_WATERMARK["hangman"]:
        _refill(kind, job)

    candidates = unseen or active
    return random.choice(candidates) if candidates else None


# --------------------------------------------------------------------------- #
# Quiz
# --------------------------------------------------------------------------- #


def _quiz_job() -> None:
    QuizQuestion = _model("QuizQuestion")
    existing = [q.question for q in QuizQuestion.query.all()]
    result = generate_quiz(
        topic=random.choice(QUIZ_TOPICS),
        difficulty=random.choice(DIFFICULTIES),
        count=BATCH["quiz"],
        exclude=existing,
    )
    known = {_key(q) for q in existing}
    added = 0
    for item in result.items:
        k = _key(item["question"])
        if k in known:
            continue
        known.add(k)
        db.session.add(
            QuizQuestion(
                question=item["question"],
                options=item["options"],
                correct_index=item["correct_index"],
                is_active=True,
            )
        )
        added += 1
    db.session.commit()
    logger.info("Content top-up (quiz): %d new questions", added)


def pick_quiz_questions(user_id: int, count: int = 10) -> List[Any]:
    """`count` active questions, unseen ones first. May return fewer if the pool is small."""
    QuizQuestion = _model("QuizQuestion")
    active = QuizQuestion.query.filter_by(is_active=True).all()
    if len(active) < count:
        _refill("quiz", _quiz_job, force=True)
        active = QuizQuestion.query.filter_by(is_active=True).all()

    seen = _recent_values(user_id, "quiz", "question_ids")
    unseen = [q for q in active if q.id not in seen]
    if len(unseen) < LOW_WATERMARK["quiz"]:
        _refill("quiz", _quiz_job)

    repeated = [q for q in active if q.id in seen]
    random.shuffle(unseen)
    random.shuffle(repeated)
    return (unseen + repeated)[:count]
