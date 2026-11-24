import hashlib, hmac, secrets, time
from .config import settings

def hash_secret(value: str) -> str:
    # PBKDF2-HMAC-SHA256 com salt aleatório; custo configurado para ambiente acadêmico.
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), 240_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"

def verify_secret(value: str, encoded: str) -> bool:
    try:
        _, salt, expected = encoded.split("$", 2)
        actual = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), 240_000).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, AttributeError):
        return False

def create_token(user_id: int, role: str) -> str:
    payload = f"{user_id}:{role}:{int(time.time()) + settings.session_ttl_seconds}"
    sig = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def read_token(token: str):
    try:
        user_id, role, expiry, signature = token.split(":")
        payload = f"{user_id}:{role}:{expiry}"
        expected = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expiry) < int(time.time()):
            return None
        return {"id": int(user_id), "role": role}
    except (ValueError, TypeError):
        return None
