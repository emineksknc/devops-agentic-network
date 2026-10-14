"""Secret sifreleme: Fernet (AES + HMAC). Anahtar sirasi: DAN_SECRET_KEY env, yoksa data/secret.key.

Dosya anahtari ilk kullanimda uretilir (data/ klasoru gitignore'lu). .env'ye DOKUNULMAZ.
Bellekteki duz metinler loglanmaz; cozme hatasi fail-closed (hata yukari).
"""
import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger("dan.secrets")

PREFIX = "fernet:"


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _key_file() -> Path:
    p = _root() / "data" / "secret.key"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_key() -> bytes:
    env_key = (os.environ.get("DAN_SECRET_KEY") or "").strip()
    if env_key:
        try:
            raw = base64.urlsafe_b64decode(env_key)
            if len(raw) != 32:
                raise ValueError("32 bayt olmali")
            return env_key.encode()
        except Exception as e:
            raise ValueError(f"DAN_SECRET_KEY gecersiz: {e}")
    kf = _key_file()
    if kf.exists():
        return kf.read_bytes().strip()
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    kf.write_bytes(key)
    try:
        os.chmod(kf, 0o600)
    except Exception:
        pass
    logger.info("Secret anahtari uretildi: %s (yedekle, kaybedersen token'lar cozulemez)", kf)
    return key


def _fernet():
    from cryptography.fernet import Fernet

    return Fernet(_load_key())


def is_encrypted(value: str) -> bool:
    return bool(value) and value.startswith(PREFIX)


def encrypt(plain: str) -> str:
    if not plain:
        return ""
    if is_encrypted(plain):
        return plain
    return PREFIX + _fernet().encrypt(plain.encode()).decode()


def decrypt(stored: str) -> str:
    """Fernet degerleri cozer; bos ve legacy duz metin oldugu gibi doner (migrasyon yolu)."""
    if not stored or not is_encrypted(stored):
        return stored or ""
    from cryptography.fernet import InvalidToken

    try:
        return _fernet().decrypt(stored[len(PREFIX):].encode()).decode()
    except InvalidToken:
        logger.error("Secret cozulemedi (anahtar mi degisti?)")
        raise ValueError("kayitli secret cozulemedi")
