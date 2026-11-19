import hashlib
import logging

from dotenv import find_dotenv, set_key


def _looks_hashed(s: str) -> bool:
    """True if `s` looks like a lowercase SHA-256 hex digest."""
    if len(s) != 64:
        return False
    return all(c in "0123456789abcdef" for c in s.lower())


def _sha256(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest().lower()


def _persist_env(key: str, value: str) -> None:
    """Write key=value back to the project's .env file, if we can find it."""
    dotenv_path = find_dotenv(usecwd=True)
    if not dotenv_path:
        logging.warning(f"Can't persist {key} to .env — file not found")
        return
    set_key(dotenv_path, key, value, quote_mode="never")
