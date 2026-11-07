import random

from flask import Blueprint, jsonify, request, g, session
import game_sessions
from auth import login_required

GAME_ID = "tictactoe"
WIN_LENGTH = {3: 3, 5: 4}
SIZES = tuple(WIN_LENGTH)
GAMEMODES = ("ai", "two_player")
DIFFICULTIES = ("easy", "medium")
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))

# Játéklogika ----------------------------------------------------------------
class TurnException(Exception):
    def __init__(self, message, http_code):
        super().__init__(message)
        self.http_code = http_code
        self.message = message

def find_winning_fields(sign, size, table):
    length = WIN_LENGTH[size]
    for r in range(size):
        for c in range(size):
            for dr, dc in DIRECTIONS:
                fields = [(r + i * dr, c + i * dc) for i in range(length)]
                if all(0 <= wr < size and 0 <= wc < size and table[wr][wc] == sign for (wr, wc) in fields):
                        return [[wr, wc] for wr, wc in fields]
    return []


class Game:
    def __init__(self, size=3, mode="two_player", difficulty=None):
        if size not in WIN_LENGTH:
            raise ValueError("Nem támogatott táblaméret!")
        self.size = size
        self.mode = mode
        self.difficulty = difficulty
        self.table = [["" for _ in range(size)] for _ in range(size)]
        self.next = "X"
        self.status = "in progress"
        self.winning_fields = []
        self.points = 0

    def turn(self, row, column):
        if self.status != "in progress":
            raise TurnException("A játék véget ért. Kezdj egy új játékot!", 409)

        if (not isinstance(row, int) or isinstance(row, bool) or not isinstance(column, int) or isinstance(column, bool)
                or not (0 <= row < self.size) or not (0 <= column < self.size)):
            raise TurnException("Érvénytelen mező.", 400)

        if self.table[row][column] != "":
            raise TurnException("Ez a mező foglalt!", 409)

        sign = self.next
        self.table[row][column] = sign

        winner = find_winning_fields(sign, self.size, self.table)
        if winner:
            self.status = f"{sign} won!"
            self.winning_fields = winner
        elif all(field != "" for rowlist in self.table for field in rowlist):
            self.status = "draw"
        else:
            self.next = "O" if sign == "X" else "X"

    def state(self):
        return {
            "size": self.size,
            "mode": self.mode,
            "difficulty": self.difficulty,
            "table": self.table,
            "next": self.next,
            "status": self.status,
            "winning_fields": self.winning_fields,
            "points": self.points
        }

    @classmethod
    def from_state(cls, data):
        game = cls(data["size"], data["mode"], data["difficulty"])
        game.table = [list(row) for row in data["table"]]
        game.next = data["next"]
        game.status = data["status"]
        game.winning_fields = [list(row) for row in data["winning_fields"]]
        game.points = data["points"]
        return game

# Végpontok --------------------------------------------------------------------
bp = Blueprint("tictactoe", __name__, url_prefix="/tictactoe")

def _body(game, ai_move=None):
    body = game.state()
    body["ai_move"] = list(ai_move) if ai_move else None
    if game.mode == "two_player":
        body["session_wins"] = session.get("tictactoe_wins", {"X": 0, "O": 0})
    return body

@bp.route("/new-game", methods=["POST"])
@login_required
def new_game():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "two_player")
    size = data.get("size", 3)
    difficulty = data.get("difficulty", "easy")
    if mode not in GAMEMODES:
        return jsonify({"error": "Ismeretlen játékmód."}), 400
    if size not in SIZES:
            return jsonify({"error": "Ez a táblaméret nem támogatott."}), 400
    if difficulty not in DIFFICULTIES:
            return jsonify({"error": "Ez a nehézségi szint nem támogatott."}), 400

    game = Game(size, mode, difficulty if mode == "ai" else None)
    game_sessions.start(g.user.id, GAME_ID, game.state())
    return jsonify(_body(game))

@bp.route("/turn", methods=["POST"])
@login_required
def turn():
    data = request.get_json(silent=True) or {}
    current = game_sessions.get_current(g.user.id, GAME_ID)
    if current is None:
        return jsonify({"error": "Nincsen aktív játék. Indíts egy újat!"}), 409

    game = Game.from_state(current.state)
    ai_move = None
    try:
        game.turn(data.get("row"), data.get("column"))
        if game.mode == "ai" and game.status == "in progress":
            ai_move = choose_ai_move(game)
            row, column = ai_move
            game.turn(row, column)
    except TurnException as e:
        return jsonify({"error": e.message}), e.http_code

    if game.status == "in progress":
        game_sessions.save_state(current, game.state())
    elif game.mode == "ai":
        match game.status:
            case "X won!":
                game.points = 1
                result = "win"
            case "O won!":
                game.points = 0
                result = "loss"
            case _:
                game.points = 0
                result = "draw"
        game_sessions.finish(current, game.state(), game.points, game.difficulty,
                             details={"size": game.size, "result": result})
    else:
        game_sessions.finish(current, game.state())
        if game.status != "draw":
            winner = "X" if game.status == "X won!" else "O"
            wins = dict(session.get("tictactoe_wins", {"X": 0, "O": 0}))
            wins[winner] += 1
            session["tictactoe_wins"] = wins
    return jsonify(_body(game, ai_move))

@bp.route("/state", methods=["GET"])
@login_required
def state():
    current = game_sessions.get_current(g.user.id, GAME_ID)
    if current is None:
        return jsonify({"error": "Még nincs aktív játék. Indíts újat!"}), 404
    return jsonify(_body(Game.from_state(current.state)))

# Gépi játékos logika ------------------------------------------------------------------
def _free_cells(game):
    return [(r, c) for r in range(game.size) for c in range(game.size) if game.table[r][c] == ""]

def choose_ai_move(game):
    free_cells = _free_cells(game)
    match game.difficulty:
        case "easy":
            return random.choice(free_cells)
        case "medium":
            mine = game.next
            theirs = "X" if mine == "O" else "O"
            for sign in (mine, theirs):
                for r, c in free_cells:
                    game.table[r][c] = sign
                    line = find_winning_fields(sign, game.size, game.table)
                    game.table[r][c] = ""
                    if line:
                        return r, c
            center = game.size // 2
            if game.table[center][center] == "":
                return center, center

            def next_to_mine(row, col):
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr = row + dr
                        nc = col + dc
                        if (dr, dc) != (0, 0) and 0 <= nr < game.size and 0 <= nc < game.size:
                            if game.table[nr][nc] == mine:
                                return True
                return False

            near_mine = [cell for cell in free_cells if next_to_mine(*cell)]
            return random.choice(near_mine or free_cells)

        case _:
            return None






