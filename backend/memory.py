
from backend.db import get_session
from backend.models import ChatMessage

MAX_MEMORY_TURNS = 5  # 5 user+assistant pairs


def add_message(corpus_id: int, role: str, content: str):
    with get_session() as s:
        s.add(ChatMessage(corpus_id=corpus_id, role=role, content=content))


def get_history(corpus_id: int):
    with get_session() as s:
        rows = (s.query(ChatMessage)
                  .filter(ChatMessage.corpus_id == corpus_id)
                  .order_by(ChatMessage.timestamp.asc()).all())
        return [{"role": r.role, "content": r.content,
                 "timestamp": r.timestamp} for r in rows]


def clear_history(corpus_id: int):
    with get_session() as s:
        (s.query(ChatMessage)
           .filter(ChatMessage.corpus_id == corpus_id).delete())


def get_recent_memory(corpus_id: int, max_turns: int = MAX_MEMORY_TURNS):
    """Return last `max_turns` user/assistant pairs in chronological order."""
    hist = get_history(corpus_id)
    pairs, cur = [], {}
    for m in hist:
        if m["role"] == "user":
            cur = {"user": m["content"]}
        elif m["role"] == "assistant" and "user" in cur:
            cur["assistant"] = m["content"]
            pairs.append(cur)
            cur = {}
    return pairs[-max_turns:]


def format_memory_for_prompt(corpus_id: int) -> str:
    pairs = get_recent_memory(corpus_id)
    if not pairs:
        return ""
    lines = ["Previous Conversation:"]
    for p in pairs:
        lines.append(f"User: {p['user']}")
        lines.append(f"A: {p.get('assistant','')}")
    return "\n".join(lines) + "\n"