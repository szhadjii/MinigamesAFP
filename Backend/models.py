from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utcnow():
    return datetime.now(UTC)


class User(db.Model):
    tablename = "users"

    id = db.Column(db.integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="player")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_string(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at
        }


class Score(db.Model):
    tablename = "scores"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    game = db.Column(db.String(20), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.String(10))
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_string(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "game": self.game,
            "points": self.points,
            "difficulty": self.difficulty,
            "details": self.details,
            "created_at": self.created_at
        }


class GameSession(db.Model):
    tablename = "game_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    game = db.Column(db.String(20), nullable=False)
    state = db.Column(db.JSON)
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    finished_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    status = db.Column(db.String(10), nullable=False, default="active")


class Word(db.Model):
    tablename = "words"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_string(self):
        return {
            "id": self.id,
            "text": self.text,
            "is_active": self.is_active
        }


class TypingText(db.Model):
    tablename = "typing_texts"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(600), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_string(self):
        return {
            "id": self.id,
            "text": self.text,
            "is_active": self.is_active
        }
