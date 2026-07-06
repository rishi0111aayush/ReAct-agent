"""
cache.py — Redis client with graceful no-op fallback.

If Redis is unavailable (local dev or connection error),
every operation silently becomes a no-op so the app works normally.

Key namespaces:
  boozo:search:{hash}   — DuckDuckGo results          TTL 1 h
  boozo:url:{hash}      — scraped webpage content     TTL 24 h
  boozo:mem:{user_id}   — per-user persistent memory  no TTL
  boozo:rl:{identifier} — rate-limit counters         TTL 60 s
"""
import hashlib
import json

import redis

from app.config import REDIS_URL, RATE_LIMIT_RPM

_TTL = {
    "search": 3_600,   # 1 hour
    "url":    86_400,  # 24 hours
}
_RATE_WINDOW = 60  # seconds


class _RedisCache:
    def __init__(self) -> None:
        self._r: redis.Redis | None = None

    # ── connection ────────────────────────────────────────────────────────────
    def _client(self) -> redis.Redis | None:
        if self._r is not None:
            return self._r
        try:
            r = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            r.ping()
            self._r = r
        except Exception:
            self._r = None
        return self._r

    def is_available(self) -> bool:
        return self._client() is not None

    # ── helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:20]

    # ── generic primitives ────────────────────────────────────────────────────
    def get(self, key: str):
        try:
            r = self._client()
            if r is None:
                return None
            raw = r.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception:
            return None

    def set(self, key: str, value, ttl: int = 0) -> None:
        try:
            r = self._client()
            if r is None:
                return
            serialised = json.dumps(value, ensure_ascii=False)
            if ttl:
                r.setex(key, ttl, serialised)
            else:
                r.set(key, serialised)
        except Exception:
            pass

    def delete(self, key: str) -> None:
        try:
            r = self._client()
            if r is None:
                return
            r.delete(key)
        except Exception:
            pass

    # ── web search cache ──────────────────────────────────────────────────────
    def get_search(self, query: str) -> str | None:
        return self.get(f"boozo:search:{self._hash(query)}")

    def set_search(self, query: str, result: str) -> None:
        self.set(f"boozo:search:{self._hash(query)}", result, _TTL["search"])

    # ── url / page-fetch cache ────────────────────────────────────────────────
    def get_url(self, url: str) -> str | None:
        return self.get(f"boozo:url:{self._hash(url)}")

    def set_url(self, url: str, content: str) -> None:
        self.set(f"boozo:url:{self._hash(url)}", content, _TTL["url"])

    # ── persistent user memory ────────────────────────────────────────────────
    def memory_append(self, user_id: str, fact: str) -> None:
        try:
            r = self._client()
            if r is None:
                return
            r.rpush(f"boozo:mem:{user_id}", fact)
        except Exception:
            pass

    def memory_get_all(self, user_id: str) -> list[str]:
        try:
            r = self._client()
            if r is None:
                return []
            return r.lrange(f"boozo:mem:{user_id}", 0, -1) or []
        except Exception:
            return []

    def memory_clear(self, user_id: str) -> None:
        self.delete(f"boozo:mem:{user_id}")

    # ── rate limiting (fixed window via INCR + EXPIRE) ────────────────────────
    def check_rate_limit(self, identifier: str) -> tuple[bool, int]:
        """
        Returns (allowed, current_count).
        Falls back to (True, 0) if Redis unavailable — no false blocks.
        """
        try:
            r = self._client()
            if r is None:
                return True, 0
            key  = f"boozo:rl:{identifier}"
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, _RATE_WINDOW)
            count = pipe.execute()[0]
            return count <= RATE_LIMIT_RPM, count
        except Exception:
            return True, 0


# singleton used across the app
cache = _RedisCache()
