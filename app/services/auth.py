import secrets
import string
from datetime import datetime, timezone

from app.domain.models import User
from app.extensions import db
from app.services.commit import try_commit
from app.services.result import Err, Ok, Result
from werkzeug.security import check_password_hash, generate_password_hash

LOGIN_MIN = 3
LOGIN_MAX = 64
PASSWORD_MIN = 12
PASSWORD_MAX = 255


def _utcnow():
    return datetime.now(timezone.utc)


# Одиночные эмодзи (без ZWJ), чтобы len() был предсказуем
_PASSWORD_EMOJIS = (
    "😀😁😂🤣😃😄😅😆😉😊😋😎😍😘🥰🤔🤨😏😮😯😪😴😌😛😜😝🤤😒😓😔😕🙃"
    "🤑😲😖😞😟😤😢😭😦😧😨😩🤯😬😰😱🥵🥶😳🤪😵😡😠🤬😷🤒🤕🤢🤮🥴😇🥳"
    "🥺🤡🤠😈👿💀👻👽👾🤖💩🎃😺😸😹😻😼😽🙀😿😾🙈🙉🙊💥💫⭐🌟✨🔥🌈"
    "🍎🍊🍋🍉🍇🍓🍒🍑🥝🍅🍆🥑🥦🌶️🥕🍞🧀🍕🌮🍣🍦🍩🍪☕🍵🍺🍻🥂🍷🥤"
)

_PASSWORD_ALPHABET = (
    string.ascii_letters
    + string.digits
    + string.punctuation
    + _PASSWORD_EMOJIS
)


def make_password(length: int = 28) -> str:
    """Криптостойкий пароль: буквы + цифры + пунктуация + эмодзи."""
    length = max(8, min(int(length or 28), 64))
    rng = secrets.SystemRandom()
    required = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(string.punctuation),
        secrets.choice(_PASSWORD_EMOJIS),
        secrets.choice(_PASSWORD_EMOJIS),
    ]
    rest = [secrets.choice(_PASSWORD_ALPHABET) for _ in range(length - len(required))]
    chars = required + rest
    rng.shuffle(chars)
    return "".join(chars)


def normalize_login(login: str) -> str:
    return (login or "").strip()


def valid_login(login: str) -> bool:
    return LOGIN_MIN <= len(login) <= LOGIN_MAX and all(
        char.isalnum() or char in "._-@" for char in login
    )


def valid_password(password: str) -> bool:
    return PASSWORD_MIN <= len(password) <= PASSWORD_MAX


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="scrypt")


def verify_password(user: User, password: str, *, migrate_legacy: bool = True) -> bool:
    stored = user.password or ""
    hashed = stored.startswith(("scrypt:", "pbkdf2:"))
    valid = check_password_hash(stored, password) if hashed else secrets.compare_digest(stored, password)
    if valid and not hashed and migrate_legacy:
        user.password = hash_password(password)
        db.session.commit()
    return valid


def register(login: str, password: str) -> Result[User]:
    login = normalize_login(login)
    password = password or ""
    if not valid_login(login):
        return Err("invalid_login")
    if not valid_password(password):
        return Err("invalid_password")
    if User.query.filter_by(login=login).first():
        return Err("login_taken")
    # nickname по умолчанию = login (можно сменить позже)
    if User.query.filter_by(nickname=login).first():
        return Err("login_taken")
    user = User(login=login, password=hash_password(password), nickname=login)
    db.session.add(user)
    if not try_commit():
        return Err("login_taken")
    return Ok(user)


def authenticate(login: str, password: str) -> tuple[bool, User | None]:
    login = normalize_login(login)
    password = password or ""
    if not login or not password:
        return False, None
    user = User.query.filter_by(login=login).first()
    if not user or getattr(user, "is_guest", False):
        return False, None
    if not verify_password(user, password):
        return False, None
    user.last_login_at = _utcnow()
    db.session.commit()
    return True, user
