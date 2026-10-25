from models import GameSession, db, utcnow


def start(user_id, game, state):
    session = GameSession(user_id=user_id, game=game, state=state, status="active")
    db.session.add(session)
    db.session.commit()
    return session

def get_current(user_id, game):
    return (GameSession.query.filter(
            GameSession.user_id == user_id,
            GameSession.game == game,
            GameSession.status.in_("active", "finished"),
        ).order_by(GameSession.id.desc()).first()
    )

def get_active(user_id, game):
    return GameSession.query.filter(user_id=user_id, game=game, status="active").first()

def save_state(session, state):
    session.state = state
    db.session.commit()

def finish(session, state, points=None, difficulty=None, details=None):
    if session.status != "active":
        raise ValueError("A játék már lezárult.")
    session.state = state
    session.status = "finished"
    session.finished_at = utcnow
    if points is not None:
        save_score(session.user_id, session.game, points, difficulty, details)
    db.session.commit()
