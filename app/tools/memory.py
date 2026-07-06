"""
tools/memory.py — Per-user persistent memory: remember, recall.

Memory is stored in Redis under key boozo:mem:{user_id}.
Requires the user to be logged in (user_id set via set_user_context).
"""
from app.cache import cache

_current_user_id: str | None = None


def set_user_context(user_id: str | None) -> None:
    global _current_user_id
    _current_user_id = user_id


def remember(fact: str) -> str:
    """Store a fact in the user's persistent Redis memory."""
    if not _current_user_id:
        return "Memory requires you to be logged in."
    cache.memory_append(_current_user_id, fact)
    return f"Remembered: {fact}"


def recall(topic: str) -> str:
    """Retrieve facts from the user's persistent Redis memory relevant to topic."""
    if not _current_user_id:
        return "Memory requires you to be logged in."
    facts = cache.memory_get_all(_current_user_id)
    if not facts:
        return "No memories stored yet. Use remember(fact) to store something."
    topic_words = set(topic.lower().split())
    relevant    = [f for f in facts if any(w in f.lower() for w in topic_words)]
    chosen      = relevant if relevant else facts[-10:]
    return "Memories:\n" + "\n".join(f"- {f}" for f in chosen)
