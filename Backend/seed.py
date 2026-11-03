from werkzeug.security import generate_password_hash

from Backend.models import Word, db, TypingText, User

SEED_WORDS = [
    "alma", "körte", "szilva", "barack", "cseresznye", "számítógép", "billentyűzet", "egyetem",
    "programozás", "adatbázis", "böngésző", "fejlesztő", "hálózat", "kutya", "macska", "folyó",
    "hegység", "tavasz", "iskola", "könyvtár", "telefon", "ablak", "asztal", "hajó", "repülő",
    "vonat", "kerékpár", "csillag", "fagylalt", "napsütés",
]

SEED_TEXTS = [
    "A gyors barna róka átugrotta a lusta kutyát, majd eltűnt az erdő sűrűjében.",
    "Aki korán kel, aranyat lel, de aki időben elmegy aludni, az reggel is mosolyogva ébred.",
    "A programozás nem varázslat: apró lépésekből áll, és minden hibából tanulunk valamit.",
    "Tavasszal a Duna partján sétálva hosszan lehet nézni, ahogy a hajók lassan elúsznak.",
    "Egy jó csapatban mindenki tudja a saját feladatát, és időben szól, ha segítségre van szüksége.",
    "A sakktábla hatvannégy mezőjén annyi lehetőség rejlik, hogy két játszma ritkán egyezik meg.",
]

def seed_database(app):
    if Word.query.count() == 0:
        db.session.add_all(Word(text=text) for text in SEED_WORDS)
    if TypingText.query.count() == 0:
        db.session.add_all(TypingText(text=text) for text in SEED_TEXTS)

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
