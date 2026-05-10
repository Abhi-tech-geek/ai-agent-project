"""AbhiNova therapist core — business logic module."""
import json
import os
import re
import hashlib
import uuid
from datetime import date, datetime, timedelta

def _hash_password(password: str, salt: bytes = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}:{hash_bytes.hex()}"

VALID_MOODS = {"sad", "anxious", "angry", "happy", "lonely", "confused", "calm", "neutral"}

_MOOD_TAG_RE = re.compile(r'<mood>\s*(\w+)\s*</mood>', re.IGNORECASE)


def parse_mood(reply: str) -> tuple[str, str, int]:
    """Extract <mood>X</mood> from first line of reply and [SCORE: X] anywhere.

    Returns (mood, stripped_reply, score). Falls back to ('neutral', original_reply, 5)
    if tags are not found.
    """
    if not reply:
        return "neutral", reply or "", 5
        
    score_match = re.search(r"\[SCORE:\s*(\d+)\]", reply)
    score = 5
    if score_match:
        try:
            score = int(score_match.group(1))
        except ValueError:
            pass
            
    # Remove score tag from reply
    reply = re.sub(r"\[SCORE:\s*\d+\]", "", reply).strip()
        
    m = _MOOD_TAG_RE.search(reply)
    if not m:
        return "neutral", reply, score

    mood = m.group(1).lower()
    if mood not in VALID_MOODS:
        return "neutral", _MOOD_TAG_RE.sub("", reply, count=1).strip(), score

    return mood, _MOOD_TAG_RE.sub("", reply, count=1).strip(), score

# ─── Crisis detection ────────────────────────────────────
CRISIS_PATTERNS = re.compile(
    r'\b(suicide|kill\s+myself|end\s+it\s+all|cant\s+go\s+on|can\'?t\s+go\s+on|'
    r'self[-\s]*harm|hurt\s+myself|'
    r'marna\s+chahta|jeena\s+nahi|khatam\s+kar(?:na|\s+du(?:n|nga))?|'
    r'mar\s+jaau(?:n|nga)?|suicide\s+karna|'
    r'apne\s+aap\s+ko\s+maar|khud\s+ko\s+maar)\b',
    re.IGNORECASE,
)


def crisis_check(text: str) -> bool:
    """Deterministic safety scan over English + romanized-Hindi crisis phrases.
    Conservative — accepts some false positives, rejects subtle false negatives.
    """
    if not text:
        return False
    return bool(CRISIS_PATTERNS.search(text))


# ─── Concern detection (replaces old skill detection) ───
CONCERN_PATTERNS = {
    'work_stress':  re.compile(r'\b(work|office|boss|deadline|kaam(\s+ka\s+pressure)?)\b', re.I),
    'anxiety':      re.compile(r'\b(anxious|anxiety|panic|ghabrahat|bechain|ghabrana)\b', re.I),
    'relationship': re.compile(r'\b(breakup|break[-\s]*up|fight|relationship|gf|bf|wife|husband|patni|pati|ladai)\b', re.I),
    'sleep':        re.compile(r'\b(insomnia|cant\s+sleep|can\'?t\s+sleep|neend\s+nahi|sone\s+nahi|so\s+nahi\s+pa)\b', re.I),
    'loneliness':   re.compile(r'\b(lonely|akela|alone|nobody|koi\s+nahi)\b', re.I),
    'grief':        re.compile(r'\b(died|death|loss|grief|guzar\s+gaye?|chala\s+gaya|nahi\s+rahe?)\b', re.I),
    'self_esteem':  re.compile(r'\b(worthless|hate\s+myself|kuch\s+nahi\s+hu|bekar|nakaam)\b', re.I),
}

VALID_THEMES = set(CONCERN_PATTERNS.keys())

SESSION_END_PATTERNS = re.compile(
    r"^\s*(bye|goodbye|thanks|thank\s+you|end\s+session|that's\s+all|thats\s+all)\s*[.!?]*\s*$",
    re.IGNORECASE,
)


def should_offer_session_summary(text: str) -> bool:
    """Return True when a user message sounds like a natural session close."""
    if not text:
        return False
    return bool(SESSION_END_PATTERNS.search(text))


def detect_concerns(text: str) -> list[str]:
    """Word-boundary regex scan. Returns list of concern keys that match.
    Order is deterministic (sorted)."""
    if not text:
        return []
    return sorted(k for k, pat in CONCERN_PATTERNS.items() if pat.search(text))


# ─── Mood metadata (UI uses) ────────────────────────────
MOOD_COLORS = {
    'sad':      '#38bdf8',   # blue
    'anxious':  '#f59e0b',   # amber
    'angry':    '#ef4444',   # red
    'happy':    '#10b981',   # green
    'lonely':   '#a78bfa',   # purple
    'calm':     '#14b8a6',   # teal
    'confused': '#94a3b8',   # grey
    'neutral':  None,
}

MOOD_EMOJI = {
    'sad': '💙', 'anxious': '💛', 'angry': '❤️‍🔥', 'happy': '💚',
    'lonely': '💜', 'calm': '🌿', 'confused': '🌫️', 'neutral': '',
}


# ─── Profile schema v2 + multi-user ──────────────────────
SCHEMA_VERSION = 2
USERS_DB_PATH = "users.json"
PROFILES_DIR = "profiles"

if not os.path.exists(PROFILES_DIR):
    os.makedirs(PROFILES_DIR)


def _default_settings() -> dict:
    return {
        "mood_tracker": True,
        "typing_animation": True,
        "ambient_halo": True,
        "privacy_pause": False,
        "voice_input": True,
        "ai_voice_output": False,
        "recognition_language": "auto",
        "speaking_speed": 0.85,
        "auto_conversation_mode": False,
        # Phase 4 toggles
        "journal_enabled": True,
        "music_enabled": True,
        "notifications_enabled": True,
    }


def _default_profile(name: str = "") -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "name": name,
        "language_pref": "hinglish",
        "primary_concern": "",
        "support_style": "both",
        "concerns": [],
        "commitments": [],
        "session_summaries": [],
        "recurring_themes": [],
        "stats": {"total_messages": 0, "streak_days": 0, "last_active": ""},
        "memory_paused": False,
        "onboarding_step": 1,
        "onboarding_complete": False,
        "persona": "dost",
        "join_date": date.today().isoformat(),
        "timezone": "UTC",
        "settings": _default_settings(),
        # Phase 4
        "journal_entries": [],
        "music_feedback": [],
    }


from filelock import FileLock

def load_users_db() -> dict:
    try:
        if os.path.exists(USERS_DB_PATH):
            with FileLock(f"{USERS_DB_PATH}.lock", timeout=5):
                with open(USERS_DB_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
    except Exception:
        pass
    return {}


def save_users_db(db: dict) -> None:
    with FileLock(f"{USERS_DB_PATH}.lock", timeout=5):
        with open(USERS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)


def authenticate(username, password):
    db = load_users_db()
    if username in db:
        stored_pw = db[username]["password"]
        if ":" in stored_pw:
            salt_hex, hash_hex = stored_pw.split(":", 1)
            salt = bytes.fromhex(salt_hex)
            if stored_pw == _hash_password(password, salt):
                return True
        else:
            # Legacy fallback
            if stored_pw == hashlib.sha256(password.encode('utf-8')).hexdigest():
                return True
    return False


def signup(username, password, name):
    db = load_users_db()
    if username in db:
        return False, "Username already exists."
    db[username] = {"password": _hash_password(password), "name": name}
    save_users_db(db)
    # Create initial profile
    profile = _default_profile(name)
    save_user(username, profile)
    migrate_legacy_user(username)
    return True, "Success"


def get_profile_path(username: str) -> str:
    return os.path.join(PROFILES_DIR, f"{username}.json")


def save_user(username: str, data: dict) -> None:
    path = get_profile_path(username)
    with FileLock(f"{path}.lock", timeout=5):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


def load_user(username: str) -> dict:
    path = get_profile_path(username)
    try:
        if os.path.exists(path):
            with FileLock(f"{path}.lock", timeout=5):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data.setdefault("settings", {})
                    data["settings"] = {**_default_settings(), **data.get("settings", {})}
                    data.setdefault("session_summaries", [])
                    data.setdefault("recurring_themes", [])
                    data.setdefault("stats", {"total_messages": 0, "streak_days": 0, "last_active": ""})
                    return data
    except Exception:
        pass
    return _default_profile()


# ─── Legacy migration (optional, can be removed if fresh start) ───
def migrate_legacy_user(username: str):
    legacy_path = "user_profile.json"
    if os.path.exists(legacy_path):
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                old = json.load(f)
            new = _default_profile(old.get("name", ""))
            new["commitments"] = old.get("todos", [])
            old_stats = old.get("stats", {}) or {}
            new["stats"]["total_messages"] = old_stats.get("total_messages", 0)
            new["stats"]["streak_days"]    = old_stats.get("streak_days", 0)
            new["stats"]["last_active"]    = old_stats.get("last_active", "")
            save_user(username, new)
        except Exception:
            pass


# ─── Memory mutations ───────────────────────────────────
def update_concerns(username: str, text: str) -> None:
    """Detect concerns in `text` and merge into stored profile.
    No-op if memory is paused."""
    user = load_user(username)
    if user.get("memory_paused"):
        return
    found = detect_concerns(text)
    user["concerns"] = sorted(set(user.get("concerns", [])) | set(found))
    save_user(username, user)


def clear_all_data(username: str) -> None:
    """Reset profile to defaults. Used by Privacy panel 'Clear all my data'."""
    user = load_user(username)
    save_user(username, _default_profile(user.get("name", "")))


def toggle_memory_pause(username: str) -> bool:
    """Flip memory_paused. Returns the new value."""
    user = load_user(username)
    user["memory_paused"] = not user.get("memory_paused", False)
    save_user(username, user)
    return user["memory_paused"]


# ─── Stats tracking ─────────────────────────────────────
def update_stats(username: str) -> None:
    """Increment message count, update streak. Called once per user message."""
    user = load_user(username)
    stats = user.get("stats", {"total_messages": 0, "streak_days": 0, "last_active": ""})
    stats["total_messages"] = stats.get("total_messages", 0) + 1

    today = date.today().isoformat()
    last = stats.get("last_active", "")
    if last == today:
        pass
    elif last:
        try:
            diff = (date.today() - date.fromisoformat(last)).days
            if diff == 1:
                stats["streak_days"] = stats.get("streak_days", 0) + 1
            elif diff > 1:
                stats["streak_days"] = 1
        except ValueError:
            stats["streak_days"] = 1
    else:
        stats["streak_days"] = 1

    stats["last_active"] = today
    user["stats"] = stats
    save_user(username, user)


# ─── Persona definitions ──────────────────────────────
PERSONAS = {
    "friend": {
        "name": "The Friend",
        "description": "Warm, casual, and supportive. Like a close friend who just listens.",
        "prompt_addon": """Your persona is THE FRIEND.
Tone: Warm, casual, and deeply empathetic.
Style: "I hear you. That sounds really tough. Tell me more."
Language: Default to English. Use Hinglish only if the user speaks Hinglish.
Best for: Users who want informal support and validation."""
    },
    "sage": {
        "name": "The Sage",
        "description": "Peaceful, mindful, and grounding. Helps you find inner peace.",
        "prompt_addon": """Your persona is THE SAGE.
Tone: Peaceful, slow, and mindful.
Style: "Take a breath... what are you noticing in your body right now?"
Language: Default to English. Use Hinglish only if the user speaks Hinglish.
Best for: Anxiety, overthinking, and grounding."""
    },
    "coach": {
        "name": "The Coach",
        "description": "Energetic, motivating, and action-oriented. Focuses on growth.",
        "prompt_addon": """Your persona is THE COACH.
Tone: Energetic, motivating, and direct.
Style: "This is a challenge, but you are capable. Let's decide on one small step today."
Language: Default to English. Use Hinglish only if the user speaks Hinglish.
Best for: Motivation, goal-setting, and moving forward."""
    },
    "socrates": {
        "name": "The Analyst",
        "description": "Logical, objective, and structured. Breaks down complex thoughts.",
        "prompt_addon": """Your persona is THE ANALYST (Socratic).
Tone: Thoughtful, analytical, and objective.
Style: "Interesting. What evidence do you have for that thought? Let's look at it logically."
Language: Default to English. Use Hinglish only if the user speaks Hinglish.
Best for: People who prefer logic and structured thinking."""
    }
}


def get_system_prompt(username: str) -> str:
    user = load_user(username)
    user_name = user.get("name", "Friend")
    persona_key = user.get("persona", "friend")
    persona = PERSONAS.get(persona_key, PERSONAS["friend"])

    base_prompt = f"""You are a warm, empathetic AI companion trained in psychological
support techniques. Your role is NOT to diagnose or replace a real
therapist, but to listen deeply, validate emotions, and help users
feel understood.

CORE LANGUAGE RULE:
1. Always default to ENGLISH.
2. Mirror the user's language only if they use Hinglish or Hindi.
3. If the user starts in English, keep your entire response in English.
4. If the user uses Hinglish (mixed Hindi-English), respond in natural, supportive Hinglish.
5. NEVER use pure Hindi script (Devanagari) unless explicitly asked. Always use Roman script for Hinglish.

User's Name: {user_name}
Current Date: {date.today().strftime("%B %d, %Y")}

Core principles:
1. Listen first, advise later (or never unless asked)
2. Every response must acknowledge the emotion before anything else
3. Ask only ONE question per message
4. Never minimize feelings ("it could be worse" is BANNED)
5. Use the user's own words back to them
6. Be conversational, warm, human — never clinical or robotic
7. NEVER ask the same question twice in one session.
8. If user seems in crisis, always provide: iCall helpline 9152987821

Therapy techniques to use:
- Reflective listening
- Cognitive reframing (gently)
- Socratic questioning
- Validation statements
- Grounding techniques for anxiety

{persona["prompt_addon"]}

Remember: You are a FRIEND who deeply understands psychology, not a formal doctor.

OUTPUT FORMAT (STRICT):
- The FIRST line of every reply MUST be exactly: <mood>X</mood>
  where X is one of: sad, anxious, angry, happy, lonely, confused, calm, neutral.
- This tag is parsed and stripped from display. Choose the user's CURRENT mood
  (what they're feeling right now), not yours.
- After the tag, a blank line, then your warm reply.
- You MUST also append a [SCORE: X] tag anywhere in your reply, where X is an integer 1-10 assessing the user's current mood based on their last message (1=very distressed/in crisis, 5=neutral, 10=excellent).
"""
    return base_prompt


# ─── Groq client + helplines ────────────────────────────
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

HELPLINES = [
    {"name": "iCall",      "num": "9152987821",     "tel": "tel:9152987821"},
    {"name": "Vandrevala", "num": "1860-2662-345",  "tel": "tel:18602662345"},
    {"name": "AASRA",      "num": "9820466726",     "tel": "tel:9820466726"},
]


def get_client() -> OpenAI:
    """Lazy-construct the Groq client. Raises RuntimeError if GROQ_API_KEY missing
    so app.py can render a clear st.error()."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY missing — add it to .env and restart. "
            "Get a free key at https://console.groq.com"
        )
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")


# ─── Therapist streaming agent ──────────────────────────
from typing import Iterator


def therapist_agent(username: str, user_input: str, chat_history: list[dict],
                    in_crisis: bool = False) -> Iterator[dict]:
    """Generator that yields streaming chunks then a final done event.

    Yields per-chunk: {"chunk": str, "done": False}
    Yields once at end: {"chunk": "", "done": True, "reply": str, "mood": str, "crisis": bool}
    """
    # Bug fix #7: strip trailing user message if it duplicates user_input
    history = list(chat_history or [])
    if history and history[-1].get("role") == "user" and history[-1].get("content") == user_input:
        history = history[:-1]

    prior = [{"role": m["role"], "content": m["content"]}
             for m in history
             if m.get("role") in ("user", "assistant")][-10:]

    flagged = f"[CRISIS_DETECTED]\n{user_input}" if in_crisis else user_input
    messages = [{"role": "system", "content": get_system_prompt(username)}, *prior,
                {"role": "user", "content": flagged}]

    client = get_client()
    stream = client.chat.completions.create(
        model=MODEL, messages=messages, max_tokens=1024,
        stream=True, temperature=0.7,
    )
    full = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        full += delta
        yield {"chunk": delta, "done": False}

    mood, reply, score = parse_mood(full)
    yield {"chunk": "", "done": True, "reply": reply, "mood": mood, "score": score, "crisis": in_crisis}

# ─── Onboarding logic ──────────────────────────────────
ONBOARDING_STEPS = {
    1: {
        "message": "Main khush hoon ki tum yahan aaye. Main tumhara AI companion hoon — ek aisa dost jo sunna jaanta hai. Shuru karne se pehle, kya tum mujhe thoda apne baare mein batana chahoge? Bilkul pressure nahi hai. 😊",
        "options": ["Chalo shuru karte hain! 🚀"]
    },
    2: {
        "message": "Ek cheez batao — aaj kal zindagi mein kya chal raha hai? Koi bhi ek area jahan thoda stuck ya heavy feel hota ho?",
        "options": ["💼 Work/Career", "❤️ Relationships", "😰 Anxiety/Stress", "😴 Sleep/Energy", "🤔 Self-confidence", "💔 Loss/Grief", "🌀 Just feel lost", "Something else"]
    },
    3: {
        "message": "Samajh gaya. Aur ek cheez — tum chahte kya ho mujhse? Main kaise help karun?",
        "options": ["🎧 Bas sunna chahta hoon", "💡 Advice bhi chahiye", "🔄 Dono — situation ke hisaab se"]
    },
    4: {
        "message": "Last cheez — kis bhasha mein comfortable ho?",
        "options": ["🇮🇳 Hindi/Hinglish", "🇬🇧 English", "Mix — jo mood ho"]
    }
}


def get_onboarding_response(username: str, step: int, user_input: str = "") -> dict:
    user = load_user(username)
    
    if step == 2:
        if user_input:
            mapping = {
                "💼 Work/Career": "work_stress",
                "❤️ Relationships": "relationship",
                "😰 Anxiety/Stress": "anxiety",
                "😴 Sleep/Energy": "sleep",
                "🤔 Self-confidence": "self_esteem",
                "💔 Loss/Grief": "grief",
                "🌀 Just feel lost": "lost"
            }
            user["primary_concern"] = mapping.get(user_input, "other")
    elif step == 3:
        if user_input:
            mapping = {
                "🎧 Bas sunna chahta hoon": "listen_only",
                "💡 Advice bhi chahiye": "advice_needed",
                "🔄 Dono — situation ke hisaab se": "both"
            }
            user["support_style"] = mapping.get(user_input, "both")
    elif step == 4:
        if user_input:
            if "Hindi" in user_input or "Hinglish" in user_input:
                user["language_pref"] = "hinglish"
            elif "English" in user_input:
                user["language_pref"] = "english"
            else:
                user["language_pref"] = "hinglish"
            user["onboarding_complete"] = True
    
    next_step = step + 1
    user["onboarding_step"] = next_step
    save_user(username, user)
    
    if next_step in ONBOARDING_STEPS:
        return ONBOARDING_STEPS[next_step]
    return None
# Kept as an alias for backward compatibility; summarizer now uses Groq via MODEL.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")

SESSION_SUMMARY_PROMPT = """You are summarizing a therapy support session. Create a warm personal summary.

Output format (use exactly):

📋 Today's Session

🗣️ What we talked about:
[2-3 lines on main topics]

💭 Your mood:
[Starting feeling] → [Ending feeling]

💡 One insight:
[Key realization or shift, in their words]

🌱 One small step:
[Tiny doable action for tomorrow, max 2 minutes to do]

💜 Closing:
[One warm personal sentence using their name]

Rules:
- Use user's own words where possible
- Max 150 words total
- Warm tone, never clinical
- If session was heavy, be extra gentle
- Never evaluate or grade the session
- Language: English"""

TOPIC_LABELS = {
    "work_stress": "work",
    "anxiety": "anxiety",
    "relationship": "relationships",
    "sleep": "sleep",
    "loneliness": "loneliness",
    "grief": "grief",
    "self_esteem": "confidence",
}


def get_claude_client():
    """Deprecated. Summarizer now uses Groq (`get_client()`).
    Kept as a backward-compat shim — returns the Groq client."""
    return get_client()


def _chat_lines(chat_history: list[dict]) -> str:
    lines = []
    for msg in chat_history or []:
        if msg.get("summary_prompt"):
            continue
        role = msg.get("role", "unknown")
        content = (msg.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content[:800]}")
    return "\n".join(lines[-60:])


def _extract_claude_text(response) -> str:
    blocks = getattr(response, "content", []) or []
    parts = []
    for block in blocks:
        if isinstance(block, dict):
            text = block.get("text", "")
        else:
            text = getattr(block, "text", "")
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _cap_words(text: str, limit: int = 150) -> str:
    words = (text or "").split()
    if len(words) <= limit:
        return text.strip()
    return " ".join(words[:limit]).rstrip(".,;:") + "..."


def extract_session_topics(chat_history: list[dict]) -> list[str]:
    text = "\n".join((m.get("content") or "") for m in chat_history or [])
    topics = [TOPIC_LABELS[c] for c in detect_concerns(text) if c in TOPIC_LABELS]
    return topics[:5]


def session_mood_bounds(chat_history: list[dict]) -> tuple[int | None, int | None]:
    scores: list[int] = []
    for msg in chat_history or []:
        score = msg.get("score")
        if isinstance(score, int) and 1 <= score <= 10:
            scores.append(score)
    if not scores:
        return None, None
    return scores[0], scores[-1]


def normalize_session_summary(summary: dict) -> dict:
    now = datetime.now()
    mood_arc = summary.get("mood_arc") or []
    mood_start = summary.get("moodStart")
    mood_end = summary.get("moodEnd")
    if mood_start is None and mood_arc:
        mood_start = mood_arc[0]
    if mood_end is None and mood_arc:
        mood_end = mood_arc[-1]
    topics = summary.get("topics") or summary.get("themes") or []
    return {
        "id": summary.get("id") or str(uuid.uuid4()),
        "date": summary.get("date") or now.date().isoformat(),
        "time": summary.get("time") or now.strftime("%H:%M"),
        "durationMinutes": summary.get("durationMinutes", 0),
        "messageCount": summary.get("messageCount", 0),
        "summary": summary.get("summary", ""),
        "moodStart": mood_start,
        "moodEnd": mood_end,
        "topics": topics,
        "persona": summary.get("persona", ""),
        "mood_arc": mood_arc,
        "themes": summary.get("themes", topics),
    }


def session_summary(
    chat_history: list[dict],
    username: str | None = None,
    duration_minutes: int | None = None,
    mood_score: int | None = None,
) -> dict:
    """Generate a warm Claude session summary and return the Phase 3 record shape."""
    now = datetime.now()
    user = load_user(username) if username else _default_profile()
    mood_start, mood_end = session_mood_bounds(chat_history)
    if mood_score is not None:
        mood_end = mood_score
    topics = extract_session_topics(chat_history)
    convo = _chat_lines(chat_history)
    user_name = user.get("name") or "there"

    prompt = (
        f"User name: {user_name}\n"
        f"Persona: {user.get('persona', 'dost')}\n"
        f"Mood start: {mood_start if mood_start is not None else 'unknown'}\n"
        f"Mood end: {mood_end if mood_end is not None else 'unknown'}\n"
        f"Detected topics: {', '.join(topics) if topics else 'unknown'}\n\n"
        f"Full conversation:\n{convo}"
    )

    # Switched to Groq (reuse GROQ_API_KEY) — no separate Anthropic key required.
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=420,
        temperature=0.4,
        messages=[
            {"role": "system", "content": SESSION_SUMMARY_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    summary_text = _cap_words(response.choices[0].message.content or "", 150)
    themes = [key for key, label in TOPIC_LABELS.items() if label in topics]
    return {
        "id": str(uuid.uuid4()),
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M"),
        "durationMinutes": int(duration_minutes or 0),
        "messageCount": len([m for m in chat_history or [] if not m.get("summary_prompt")]),
        "summary": summary_text,
        "moodStart": mood_start,
        "moodEnd": mood_end,
        "topics": topics,
        "persona": user.get("persona", "dost"),
        # Backward-compatible keys for older dashboard/privacy code and tests.
        "mood_arc": [m for m in (mood_start, mood_end) if m is not None],
        "themes": themes,
    }


def commit_session_summary(
    username: str,
    chat_history: list[dict],
    duration_minutes: int | None = None,
) -> dict | None:
    """Append a Phase 3 session summary and recompute recurring themes."""
    user = load_user(username)
    real_messages = [m for m in chat_history or [] if not m.get("summary_prompt")]
    if user.get("memory_paused") or len(real_messages) < 4:
        return None
    summ = session_summary(real_messages, username=username, duration_minutes=duration_minutes)
    user["session_summaries"] = (user.get("session_summaries", []) + [summ])[-100:]

    counts: dict[str, int] = {}
    for s in user["session_summaries"]:
        for topic in normalize_session_summary(s).get("topics", []):
            counts[topic] = counts.get(topic, 0) + 1
    user["recurring_themes"] = sorted(counts, key=lambda k: counts[k], reverse=True)[:3]
    save_user(username, user)
    return summ


def delete_session_summary(username: str, summary_id: str) -> bool:
    user = load_user(username)
    before = len(user.get("session_summaries", []))
    user["session_summaries"] = [
        s for s in user.get("session_summaries", [])
        if normalize_session_summary(s).get("id") != summary_id
    ]
    save_user(username, user)
    return len(user["session_summaries"]) != before


# ─── Profile editing (for sidebar) ──────────────────────
def update_profile(username: str, name: str | None = None, language_pref: str | None = None, persona: str | None = None) -> dict:
    """Patch top-level profile fields. None = leave unchanged."""
    user = load_user(username)
    if name is not None:
        user["name"] = name
    if language_pref is not None and language_pref in {"hinglish", "english", "hindi"}:
        user["language_pref"] = language_pref
    if persona is not None:
        user["persona"] = persona
    save_user(username, user)
    return user


patch_profile = update_profile

def add_mood_log(username, date_str, time_str, morning_score, tags, sleep_quality, one_word, from_chat=False, chat_mood_score=None):
    user = load_user(username)
    if "mood_logs" not in user:
        user["mood_logs"] = []
        
    # Check if a log for this date already exists
    existing = next((l for l in user["mood_logs"] if l.get("date") == date_str), None)
    
    if existing:
        if morning_score is None and chat_mood_score is not None:
            existing["chatMoodScore"] = chat_mood_score
        else:
            existing["eveningScore"] = morning_score # Treat secondary update as evening score
        log = existing
    else:
        log = {
            "id": str(uuid.uuid4()),
            "date": date_str,
            "time": time_str,
            "morningScore": morning_score,
            "eveningScore": None,
            "tags": tags,
            "sleepQuality": sleep_quality,
            "oneWord": one_word,
            "fromChat": from_chat,
            "chatMoodScore": chat_mood_score
        }
        user["mood_logs"].append(log)
        
    save_user(username, user)
    return log

def get_dashboard_stats(username):
    user = load_user(username)
    logs = user.get("mood_logs", [])
    
    if not logs:
        return {"avg_mood": 0, "good_days": 0, "total_sessions": 0, "logs": []}
        
    scores = [l["morningScore"] for l in logs if l.get("morningScore")]
    avg_mood = sum(scores) / len(scores) if scores else 0
    good_days = sum(1 for s in scores if s >= 6)
    
    return {
        "avg_mood": round(avg_mood, 1),
        "good_days": good_days,
        "total_sessions": user.get("stats", {}).get("total_messages", 0),
        "logs": logs
    }

def check_achievements(username):
    user = load_user(username)
    logs = user.get("mood_logs", [])
    achievements = user.get("achievements", [])
    new_unlocks = []
    
    def unlock(ach_id):
        if ach_id not in achievements:
            achievements.append(ach_id)
            new_unlocks.append(ach_id)
            
    if len(logs) >= 1:
        unlock("First Step")
        
    streak = user.get("stats", {}).get("streak_days", 0)
    if streak >= 7:
        unlock("7 Days")
        
    if streak >= 30:
        unlock("One Month")
        
    if new_unlocks:
        user["achievements"] = achievements
        save_user(username, user)

    return new_unlocks


# ════════════════════════════════════════════════════════
# ═══   PHASE 4 — THOUGHT JOURNAL (CBT)                ═══
# ════════════════════════════════════════════════════════

DISTORTION_LABELS = {
    "all_or_nothing":         "All-or-Nothing Thinking",
    "catastrophizing":        "Catastrophizing",
    "mind_reading":           "Mind Reading",
    "personalization":        "Personalization",
    "should_statements":      "Should Statements",
    "emotional_reasoning":    "Emotional Reasoning",
    "overgeneralization":     "Overgeneralization",
    "discounting_positives":  "Discounting the Positives",
    "balanced":               "Balanced Thinking",
}


def _extract_json(text: str) -> dict:
    """Find the first { ... } block in `text` and parse it. LLMs sometimes
    add prose around JSON; this is forgiving."""
    if not text:
        return {}
    text = text.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Greedy match the first {...} that balances
    depth, start = 0, -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                blob = text[start:i + 1]
                # Replace single quotes -> double quotes only on key/value boundaries
                # Try strict parse first; fall back with quote swap.
                for candidate in (blob, blob.replace("'", '"')):
                    try:
                        return json.loads(candidate)
                    except Exception:
                        continue
                return {}
    return {}


def _journal_chat(system_prompt: str, user_prompt: str, max_tokens: int = 400) -> dict:
    """Call the LLM with a JSON-only system prompt. Returns parsed dict or {}."""
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=0.5,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = (response.choices[0].message.content or "").strip()
    return _extract_json(raw)


def journal_generate_questions(thought: str, intensity: int) -> dict:
    """Step 2: produce two gentle, curious examination questions."""
    system = (
        "You receive a user's distressing thought and an intensity score.\n"
        "Return EXACTLY 2 gentle, curious questions to help them examine the thought.\n"
        "Rules:\n"
        "- Questions must be genuinely curious, not leading\n"
        "- Help the user see the thought from outside\n"
        "- Do not invalidate the feeling\n"
        "- Each question under 15 words\n"
        "Return ONLY valid JSON, no prose:\n"
        '{"q1": "question one", "q2": "question two"}'
    )
    user = f"Thought: {thought}\nIntensity: {int(intensity)}/10"
    data = _journal_chat(system, user, max_tokens=200)
    q1 = (data.get("q1") or "").strip()
    q2 = (data.get("q2") or "").strip()
    if not q1 or not q2:
        # Safe fallback so the UI never dead-ends
        q1 = q1 or "What evidence do you have that this thought is fully true?"
        q2 = q2 or "If a close friend told you this, how would you respond?"
    return {"q1": q1, "q2": q2}


def journal_identify_distortion(thought: str, answers: list[str]) -> dict:
    """Step 3: classify thought into one cognitive distortion (or 'balanced')."""
    valid = [
        "all_or_nothing", "catastrophizing", "mind_reading", "personalization",
        "should_statements", "emotional_reasoning", "overgeneralization",
        "discounting_positives", "balanced",
    ]
    system = (
        "You receive a user's thought and their answers to two reflective questions.\n"
        "Identify ONE cognitive distortion if clearly present, else return 'balanced'.\n"
        f"Allowed values for `distortion`: {', '.join(valid)}\n"
        "Return ONLY valid JSON, no prose:\n"
        '{"distortion": "all_or_nothing", "name": "All-or-Nothing Thinking", '
        '"explanation": "one warm sentence explaining this pattern simply", '
        '"in_their_words": "one sentence showing how it appears in their thought"}'
    )
    answer_text = "\n".join(f"A{i+1}: {a}" for i, a in enumerate(answers or []))
    user = f"Thought: {thought}\n{answer_text}"
    data = _journal_chat(system, user, max_tokens=300)
    distortion = (data.get("distortion") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if distortion not in valid:
        distortion = "balanced"
    name = (data.get("name") or DISTORTION_LABELS.get(distortion, "Balanced Thinking")).strip()
    explanation = (data.get("explanation") or "").strip()
    in_their_words = (data.get("in_their_words") or "").strip()
    if distortion == "balanced" and not explanation:
        explanation = (
            "This looks like a balanced thought. Sometimes our minds are just "
            "processing something genuinely difficult."
        )
    return {
        "distortion": distortion,
        "name": name,
        "explanation": explanation,
        "in_their_words": in_their_words,
    }


def journal_generate_reframe(thought: str, answers: list[str], distortion: str) -> dict:
    """Step 4: gentle reframe acknowledging pain first."""
    system = (
        "You write a gentle reframe of a user's thought.\n"
        "Rules:\n"
        "- Acknowledge the pain first\n"
        "- Not toxic positivity — be realistic\n"
        "- Use their own words where possible\n"
        "- End with something empowering\n"
        "- Max 2-3 sentences total\n"
        "Return ONLY valid JSON, no prose:\n"
        '{"reframe": "the reframed thought", "note": "one line on why this helps"}'
    )
    answer_text = "\n".join(f"A{i+1}: {a}" for i, a in enumerate(answers or []))
    user = (
        f"Original thought: {thought}\n"
        f"{answer_text}\n"
        f"Distortion identified: {distortion}"
    )
    data = _journal_chat(system, user, max_tokens=300)
    reframe = (data.get("reframe") or "").strip()
    note = (data.get("note") or "").strip()
    if not reframe:
        reframe = (
            "What you feel is real and valid. The thought may be one true angle, "
            "not the only one — and you've already started looking at it more clearly."
        )
    if not note:
        note = "Naming the pattern softens its grip."
    return {"reframe": reframe, "note": note}


def add_journal_entry(username: str, entry: dict) -> dict:
    """Persist a finished journal entry. Returns the saved record."""
    user = load_user(username)
    if user.get("memory_paused"):
        return entry
    entries = user.get("journal_entries", [])
    record = {
        "id": entry.get("id") or str(uuid.uuid4()),
        "date": entry.get("date") or date.today().isoformat(),
        "time": entry.get("time") or datetime.now().strftime("%H:%M"),
        "originalThought": entry.get("originalThought", ""),
        "intensity": int(entry.get("intensity") or 0),
        "q1": entry.get("q1", ""),
        "a1": entry.get("a1", ""),
        "q2": entry.get("q2", ""),
        "a2": entry.get("a2", ""),
        "distortion": entry.get("distortion", "balanced"),
        "distortionName": entry.get("distortionName", "Balanced Thinking"),
        "explanation": entry.get("explanation", ""),
        "inTheirWords": entry.get("inTheirWords", ""),
        "reframe": entry.get("reframe", ""),
        "note": entry.get("note", ""),
        "saved": True,
    }
    entries.append(record)
    user["journal_entries"] = entries[-200:]
    save_user(username, user)
    return record


def get_journal_entries(username: str) -> list[dict]:
    return load_user(username).get("journal_entries", [])


def delete_journal_entry(username: str, entry_id: str) -> bool:
    user = load_user(username)
    before = len(user.get("journal_entries", []))
    user["journal_entries"] = [
        e for e in user.get("journal_entries", []) if e.get("id") != entry_id
    ]
    save_user(username, user)
    return len(user["journal_entries"]) != before


def get_journal_stats(username: str) -> dict:
    """Aggregate entries for the dashboard. Month = last 30 days."""
    entries = get_journal_entries(username)
    if not entries:
        return {
            "entries_this_month": 0,
            "most_common_pattern": None,
            "avg_intensity": 0,
            "distortion_counts": {},
            "intensity_series": [],
        }
    today = date.today()
    month_ago = today - timedelta(days=30)
    in_month = []
    for e in entries:
        try:
            d = date.fromisoformat(e.get("date", ""))
        except Exception:
            continue
        if d >= month_ago:
            in_month.append(e)

    counts: dict[str, int] = {}
    for e in in_month:
        d = e.get("distortion") or "balanced"
        if d == "balanced":
            continue
        counts[d] = counts.get(d, 0) + 1
    most = max(counts.items(), key=lambda kv: kv[1])[0] if counts else None

    intensities = [int(e.get("intensity") or 0) for e in entries if e.get("intensity")]
    avg = round(sum(intensities) / len(intensities), 1) if intensities else 0

    series = [
        {"date": e.get("date"), "intensity": int(e.get("intensity") or 0)}
        for e in sorted(entries, key=lambda x: x.get("date", ""))
        if e.get("intensity")
    ]

    return {
        "entries_this_month": len(in_month),
        "most_common_pattern": DISTORTION_LABELS.get(most, most) if most else None,
        "avg_intensity": avg,
        "distortion_counts": {DISTORTION_LABELS.get(k, k): v for k, v in counts.items()},
        "intensity_series": series,
    }


# ════════════════════════════════════════════════════════
# ═══   PHASE 4 — MUSIC THERAPY                        ═══
# ════════════════════════════════════════════════════════

# Mood key → playlist + ambient sound + supportive copy
MOOD_TO_MUSIC = {
    "sad": {
        "label": "Soothing & Gentle",
        "spotifyId": "37i9dQZF1DX3YSRoSdA634",
        "ambient": "soft_rain",
        "message": (
            "Some gentle music might help. Sometimes melodies say what words cannot."
        ),
    },
    "anxious": {
        "label": "Calming & Grounding",
        "spotifyId": "37i9dQZF1DWZd79rJ6a7lp",
        "ambient": "forest_rain",
        "message": "These grounding sounds can naturally slow your breathing.",
    },
    "angry": {
        "label": "Release & Transition",
        "spotifyId": "37i9dQZF1DX3rxVfibe1L0",
        "ambient": "ocean_waves",
        "message": "Sometimes expressing feelings through music helps before calming.",
    },
    "happy": {
        "label": "Uplifting & Joyful",
        "spotifyId": "37i9dQZF1DXdPec7aLTmlC",
        "ambient": "morning_birds",
        "message": "This mood deserves a good soundtrack!",
    },
    "numb": {
        "label": "Gentle & Warming",
        "spotifyId": "37i9dQZF1DX6ziVCJnEUT5",
        "ambient": "fireplace",
        "message": "Sometimes just having something soft in the background helps.",
    },
    "focus": {
        "label": "Deep Focus",
        "spotifyId": "37i9dQZF1DWZeKCadgRdKQ",
        "ambient": "cafe",
        "message": "Lo-fi works well for concentration.",
    },
}

# Map therapist <mood> tags to music keys
MOOD_TAG_TO_MUSIC = {
    "sad":      "sad",
    "lonely":   "sad",
    "anxious":  "anxious",
    "confused": "anxious",
    "angry":    "angry",
    "happy":    "happy",
    "calm":     "focus",
    "neutral":  "focus",
}


def music_for_mood(mood_tag: str) -> dict:
    """Resolve a therapist mood tag (or direct music key) to a music block."""
    key = MOOD_TAG_TO_MUSIC.get(mood_tag, mood_tag)
    return MOOD_TO_MUSIC.get(key) or MOOD_TO_MUSIC["focus"]


def add_music_feedback(username: str, mood_key: str, ambient: str, response: str) -> dict:
    """Track 'Does this help?' answers — Yes / A little / Different."""
    user = load_user(username)
    fb = user.get("music_feedback", [])
    record = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now().isoformat(),
        "moodKey": mood_key,
        "ambient": ambient,
        "response": response,
    }
    fb.append(record)
    user["music_feedback"] = fb[-200:]
    save_user(username, user)
    return record


def consecutive_sad_messages(chat_history: list[dict], window: int = 6) -> int:
    """Count how many of the last `window` assistant turns were sad/lonely-flagged."""
    sad = {"sad", "lonely"}
    count = 0
    for m in reversed(chat_history or []):
        if m.get("role") != "assistant":
            continue
        if m.get("mood") in sad:
            count += 1
        else:
            break
        if count >= window:
            break
    return count


def export_user_data(username: str) -> dict:
    """Return the full user profile as a JSON-serializable dict for export."""
    return load_user(username)


def clear_feature_data(username: str, feature: str) -> None:
    """Wipe one feature's data while keeping the rest of the profile."""
    user = load_user(username)
    if feature == "journal":
        user["journal_entries"] = []
    elif feature == "music":
        user["music_feedback"] = []
    elif feature == "mood":
        user["mood_logs"] = []
    elif feature == "summaries":
        user["session_summaries"] = []
        user["recurring_themes"] = []
    save_user(username, user)
