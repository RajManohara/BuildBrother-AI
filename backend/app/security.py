import hashlib
import json
import re
import secrets
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Header, HTTPException, Request

SECRET_FIELDS = re.compile(r"token|password|secret|authorization|private.?key", re.I)
SECRET_VALUES = re.compile(r"(?:gh[pousr]_[A-Za-z0-9_]{10,}|github_pat_[A-Za-z0-9_]+|Bearer\s+\S+|-----BEGIN[\s\S]*?PRIVATE KEY-----[\s\S]*?-----END[\s\S]*?PRIVATE KEY-----)", re.I)


def sanitize(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if SECRET_FIELDS.search(k) else sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        value = SECRET_VALUES.sub("[REDACTED]", value)
        value = re.sub(r"(?i)\b(password|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", value)
        return value[:10000]
    return value


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def require_ingest(request: Request, authorization: str = Header(default="")):
    expected = request.app.state.settings.ingest_token
    if not expected or not secrets.compare_digest(authorization, f"Bearer {expected}"):
        raise HTTPException(401, "A dedicated ingestion credential is required")


def require_read(request: Request, authorization: str = Header(default=""), x_api_key: str = Header(default="")):
    expected = request.app.state.settings.app_api_key
    if expected and not (secrets.compare_digest(x_api_key, expected) or secrets.compare_digest(authorization, f"Bearer {expected}")):
        raise HTTPException(401, "Application credential required")


class RateLimiter:
    """Bounded per-client limiter for a single-process local MVP."""
    def __init__(self):
        self.entries = defaultdict(deque)
        self.lock = Lock()

    def allow(self, key: str, limit: int = 60) -> bool:
        with self.lock:
            instant = time.monotonic()
            for old_key in list(self.entries):
                if not self.entries[old_key] or self.entries[old_key][-1] < instant - 60:
                    del self.entries[old_key]
            queue = self.entries[key]
            while queue and queue[0] < instant - 60:
                queue.popleft()
            if len(queue) >= limit:
                return False
            queue.append(instant)
            return True
