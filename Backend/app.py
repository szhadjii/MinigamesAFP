
import os
from pathlib import Path

from flask import Flask

import admin
import auth
# import Games.hangman
# import Games.memory_game
# import Games.number_guess
# import Games.typing_game
import scores
from Games import tictactoe
from models import db
from seed import seed_database


def create_app(test_config=None):
    app = Flask(__name__, static_folder="../Frontend")
    database = Path(app.root_path, "minigames.db").as_posix()
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-csere-le-eles-hasznalat-elott"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database}",
        SESSION_COOKIE_SAMESITE="Lax",
        ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "admin1234"),
    )
    if test_config:
        app.config.from_mapping(test_config)

    db.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(scores.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(tictactoe.bp)
    # app.register_blueprint(hangman.bp)
    # app.register_blueprint(typing_game.bp)
    # app.register_blueprint(memory_game.bp)
    # app.register_blueprint(number_guess.bp)

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    with app.app_context():
        db.create_all()
        seed_database(app)

    return app

if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
