from werkzeug.security import generate_password_hash

from models import db, User


def seed_database(app):
    if User.query.filter_by(role="admin").first() is None:
        username = app.config["ADMIN_USERNAME"]
        if User.query.filter_by(username=username).first() is None:
            db.session.add(User(
                username=username,
                password_hash=generate_password_hash(app.config["ADMIN_PASSWORD"]),
                role="admin",
            ))
        else:
            print(f"FIGYELEM: nincs admin, de a(z) '{username}' név már foglalt; adj meg másik ADMIN_USERNAME-et.")
    db.session.commit()
