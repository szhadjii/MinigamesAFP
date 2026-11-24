from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from content_generator import (
    DIFFICULTIES,
    GenerationResult,
    generate_hangman_words,
    generate_quiz,
    generate_typing_texts,
)

logger = logging.getLogger(__name__)

# When a pool holds fewer items than this, a top-up is started.
LOW_WATERMARK = {"typing": 3, "hangman": 8, "quiz": 10}
# How many items one top-up asks for.
BATCH = {"typing": 5, "hangman": 15, "quiz": 15}
# Minimum seconds between two top-up attempts of the same pool (protects the API quota
# when the LLM is down).
REFILL_COOLDOWN = 60
# How many recently served items are passed to the LLM as "do not repeat these".
RECENT_LIMIT = 100

QUIZ_TOPICS = [
    "általános műveltség", "földrajz", "történelem", "természettudomány",
    "irodalom", "sport", "technika és informatika", "zene és filmek",
]

Key = Tuple[str, str]  # (kind, difficulty)

_lock = threading.Lock()
_pools: Dict[Key, List[Any]] = {}
_recent: Dict[Key, deque] = {}
_running: Set[Key] = set()
_last_attempt: Dict[Key, float] = {}
_background_refill = True


# --------------------------------------------------------------------------- #
# Setup / helpers
# --------------------------------------------------------------------------- #


def configure(background_refill: bool = True) -> None:
    global _background_refill
    _background_refill = background_refill


def reset() -> None:
    with _lock:
        _pools.clear()
        _recent.clear()
        _running.clear()
        _last_attempt.clear()


def pool_sizes() -> Dict[str, int]:
    with _lock:
        return {f"{kind}:{difficulty}": len(items) for (kind, difficulty), items in _pools.items()}


def _check_difficulty(difficulty: Optional[str]) -> str:
    if difficulty is None:
        return random.choice(DIFFICULTIES)
    difficulty = difficulty.strip().lower()
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {DIFFICULTIES}")
    return difficulty


def _text_of(item: Any) -> str:
    return item["question"] if isinstance(item, dict) else item


def _remember(key: Key, items: List[Any]) -> None:
    recent = _recent.setdefault(key, deque(maxlen=RECENT_LIMIT))
    recent.extend(_text_of(i) for i in items)


def _exclude_list(key: Key) -> List[str]:
    with _lock:
        return list(_recent.get(key, ())) + [_text_of(i) for i in _pools.get(key, ())]


def _generate(key: Key, count: int, exclude: List[str]) -> GenerationResult:
    kind, difficulty = key
    if kind == "typing":
        return generate_typing_texts(difficulty=difficulty, count=count, exclude=exclude)
    if kind == "hangman":
        return generate_hangman_words(difficulty=difficulty, count=count, exclude=exclude)
    if kind == "quiz":
        return generate_quiz(
            topic=random.choice(QUIZ_TOPICS), difficulty=difficulty, count=count, exclude=exclude
        )
    raise ValueError(f"unknown content kind {kind!r}")


# --------------------------------------------------------------------------- #
# Top-up (background)
# --------------------------------------------------------------------------- #


def _refill_job(key: Key) -> None:
    result = _generate(key, BATCH[key[0]], _exclude_list(key))
    if result.source == "fallback":
        logger.info("Top-up %s: LLM produced nothing, pool left unchanged", key)
        return
    with _lock:
        _pools.setdefault(key, []).extend(result.items)
    logger.info("Top-up %s: %d new items (%s)", key, len(result.items), result.source)


def _refill_async(key: Key) -> None:
    now = time.time()
    with _lock:
        if key in _running or now - _last_attempt.get(key, 0) < REFILL_COOLDOWN:
            return
        _running.add(key)
        _last_attempt[key] = now

    def worker() -> None:
        try:
            _refill_job(key)
        except Exception:  # noqa: BLE001
            logger.exception("Content top-up failed (%s)", key)
        finally:
            with _lock:
                _running.discard(key)

    if _background_refill:
        threading.Thread(target=worker, daemon=True, name=f"refill-{key[0]}-{key[1]}").start()
    else:
        worker()


def prewarm(kinds: Tuple[str, ...] = ("typing", "hangman", "quiz")) -> None:
    """Start filling the pools in the background (e.g. at app startup). Costs LLM calls."""
    for kind in kinds:
        for difficulty in DIFFICULTIES:
            _refill_async((kind, difficulty))


# --------------------------------------------------------------------------- #
# Serving
# --------------------------------------------------------------------------- #


def _serve(kind: str, difficulty: str, count: int) -> List[Any]:
    key = (kind, difficulty)

    with _lock:
        pool = _pools.setdefault(key, [])
        items: List[Any] = []
        while pool and len(items) < count:
            items.append(pool.pop(random.randrange(len(pool))))
        _remember(key, items)

    missing = count - len(items)
    if missing > 0:
        # Pool could not cover it: generate now (LLM, or fallback if the LLM fails).
        result = _generate(key, missing, _exclude_list(key))
        extra = list(result.items[:missing])
        with _lock:
            _remember(key, extra)
        items.extend(extra)

    with _lock:
        low = len(_pools[key]) < LOW_WATERMARK[kind]
    if low:
        _refill_async(key)
    return items


def pick_typing_text(difficulty: Optional[str] = None) -> Optional[str]:
    """One typing text (None only if there is neither LLM nor fallback content)."""
    items = _serve("typing", _check_difficulty(difficulty), 1)
    return items[0] if items else None


def pick_hangman_word(difficulty: str = "medium") -> Optional[str]:
    """One lowercase Hungarian word of the right length for the difficulty."""
    items = _serve("hangman", _check_difficulty(difficulty), 1)
    return items[0] if items else None


def pick_quiz_questions(count: int = 10, difficulty: str = "medium") -> List[Dict[str, Any]]:
    """
    `count` questions: {"question": str, "options": [4 strings], "correct_index": 0..3}.
    May return fewer if neither LLM nor fallback has enough. Keep correct_index on the
    server (e.g. in the game session state) and send content_generator.public_quiz_view()
    to the frontend.
    """
    count = max(1, min(20, int(count)))
    return _serve("quiz", _check_difficulty(difficulty), count)
