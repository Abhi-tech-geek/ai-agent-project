"""AbhiNova therapist core — business logic module."""
import json
import os
import re
import hashlib
import uuid

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

VALID_MOODS = {"sad", "anxious", "angry", "happy", "lonely", "confused", "calm", "neutral"}

_MOOD_TAG_RE = re.compile(r'^\s*<mood>\s*(\w+)\s*</mood>\s*\n?', re.IGNORECASE)


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
        
    m = _MOOD_TAG_RE.match(reply)
    if not m:
        return "neutral", reply, score
        
    mood = m.group(1).lower()
    if mood not in VALID_MOODS:
        return "neutral", _MOOD_TAG_RE.sub("", reply, count=1), score
        
    return mood, _MOOD_TAG_RE.sub("", reply, count=1), score


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
        "settings": {
            "mood_tracker": True,
            "typing_animation": True,
            "ambient_halo": True,
            "privacy_pause": False
        }
    }


def load_users_db() -> dict:
    try:
        if os.path.exists(USERS_DB_PATH):
            with open(USERS_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_users_db(db: dict) -> None:
    with open(USERS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


def authenticate(username, password):
    db = load_users_db()
    if username in db and db[username]["password"] == _hash_password(password):
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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_user(username: str) -> dict:
    path = get_profile_path(username)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
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
from datetime import date, timedelta


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
    "dost": {
        "name": "Yaar",
        "description": "🤗 The Friend - Casual, uses Hinglish/slang, informal support.",
        "prompt_addon": """Your persona is DOST (The Friend).
Tone: Casual, uses urban slang, funny when appropriate.
Style: "Arre yaar, yeh toh bahut tough situation hai!"
Language: Heavy Hinglish naturally, just like urban Indians talk.
Best for: Users who want informal support."""
    },
    "sage": {
        "name": "Ananda",
        "description": "🧘 The Sage - Peaceful, mindful, grounding.",
        "prompt_addon": """Your persona is SAGE (The Calm Guide).
Tone: Peaceful, slow, mindful.
Style: "Take a breath... aur mujhe batao, is moment mein kya feel ho raha hai tumhare andar?"
Language: Gentle Hindi/English mix.
Best for: Anxiety, overthinking."""
    },
    "coach": {
        "name": "Arjun",
        "description": "💪 The Coach - Energetic, motivating, action-oriented.",
        "prompt_addon": """Your persona is COACH (The Motivator).
Tone: Energetic, action-oriented, positive.
Style: "Sun, yeh situation tough hai — but TUM tougher ho! Chalo, ek step decide karte hain aaj."
Language: Punchy English/Hindi.
Best for: Depression, low motivation, goal-setting."""
    },
    "socrates": {
        "name": "Vivek",
        "description": "🔬 The Socrates - Logical, analytical, structured.",
        "prompt_addon": """Your persona is SOCRATES (The Logical One).
Tone: Thoughtful, analytical, structured.
Style: "Interesting. Ab yeh batao — yeh belief tumhare paas kab se hai? Koi evidence hai iske liye?"
Language: Mostly English, structured.
Best for: Overthinkers, people who like logic."""
    }
}


def get_system_prompt(username: str) -> str:
    user = load_user(username)
    user_name = user.get("name", "Dost")
    persona_key = user.get("persona", "dost")
    persona = PERSONAS.get(persona_key, PERSONAS["dost"])

    base_prompt = f"""You are a warm, empathetic AI companion trained in psychological
support techniques. Your role is NOT to diagnose or replace a real
therapist, but to listen deeply, validate emotions, and help users
feel understood.

Core principles:
1. Listen first, advise later (or never unless asked)
2. Every response must acknowledge the emotion before anything else
3. Ask only ONE question per message
4. Never minimize feelings ("it could be worse" is BANNED)
5. Use the user's own words back to them
6. Be conversational, warm, human — never clinical or robotic
7. NEVER ask the same question twice in one session. Track what you've already asked.
8. If user seems in crisis, always provide: iCall helpline 9152987821

Therapy techniques to use:
- Reflective listening
- Cognitive reframing (gently)
- Socratic questioning
- Validation statements
- Grounding techniques for anxiety

LANGUAGE RULE (HIGHEST PRIORITY):
Detect the language/style of EVERY user message.
- If user writes in Hindi -> respond in Hindi
- If user writes in English -> respond in English
- If user writes in Hinglish (mixed) -> respond in Hinglish naturally.
NEVER switch language mid-conversation unless user switches first.

Current User: {user_name}
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
def session_summary(chat_history: list[dict]) -> dict:
    """One LLM call. Returns {date, summary, mood_arc, themes}."""
    convo = "\n".join(f"{m['role']}: {(m.get('content') or '')[:200]}"
                      for m in (chat_history or [])[-30:])
    valid_themes_str = ", ".join(sorted(VALID_THEMES))
    valid_moods_str = ", ".join(sorted(VALID_MOODS))

    client = get_client()
    res = client.chat.completions.create(
        model=MODEL, max_tokens=300,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content":
             "Summarize this therapy conversation. Output strict JSON with these keys:\n"
             '  "summary": one short paragraph, no names, no quotes, just themes + arc\n'
             f'  "mood_arc": list of moods in order, each in {{{valid_moods_str}}}\n'
             f'  "themes":  list of themes touched, each in {{{valid_themes_str}}}'},
            {"role": "user", "content": convo},
        ],
    )
    try:
        data = json.loads(res.choices[0].message.content)
        data["mood_arc"] = [m for m in data.get("mood_arc", []) if m in VALID_MOODS]
        data["themes"]   = [th for th in data.get("themes", []) if th in VALID_THEMES]
        data.setdefault("summary", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        data = {"summary": "", "mood_arc": [], "themes": []}
    return {"date": date.today().isoformat(), **data}


def commit_session_summary(username: str, chat_history: list[dict]) -> None:
    """Append session summary to profile, cap at 20, recompute recurring_themes.
    No-op if memory paused or chat too short."""
    user = load_user(username)
    if user.get("memory_paused") or len(chat_history or []) < 4:
        return
    summ = session_summary(chat_history)
    user["session_summaries"] = (user.get("session_summaries", []) + [summ])[-20:]

    counts: dict[str, int] = {}
    for s in user["session_summaries"]:
        for th in s.get("themes", []):
            counts[th] = counts.get(th, 0) + 1
    user["recurring_themes"] = sorted(counts, key=lambda k: counts[k], reverse=True)[:3]
    save_user(username, user)


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
