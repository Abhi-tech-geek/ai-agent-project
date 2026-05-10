import pytest
from therapist import parse_mood, VALID_MOODS


def test_parse_mood_extracts_tag_and_strips():
    mood, body = parse_mood("<mood>sad</mood>\nHey, sun ke dukh hua.")
    assert mood == "sad"
    assert body == "Hey, sun ke dukh hua."


def test_parse_mood_invalid_falls_back_to_neutral():
    mood, body = parse_mood("<mood>furious</mood>\nblah")
    assert mood == "neutral"
    assert body == "blah"


def test_parse_mood_missing_tag_returns_neutral_and_full_text():
    mood, body = parse_mood("plain reply, no tag here")
    assert mood == "neutral"
    assert body == "plain reply, no tag here"


def test_parse_mood_handles_uppercase_tag():
    mood, body = parse_mood("<MOOD>SAD</MOOD>\nhi")
    assert mood == "sad"
    assert body == "hi"


def test_parse_mood_handles_extra_whitespace():
    mood, body = parse_mood("  <mood>  anxious  </mood>  \n\nbody text")
    assert mood == "anxious"
    assert body.strip() == "body text"


def test_valid_moods_set_has_eight_entries():
    assert VALID_MOODS == {"sad","anxious","angry","happy","lonely","confused","calm","neutral"}


# ─── crisis_check ────────────────────────────────────────
from therapist import crisis_check


def test_crisis_english_explicit():
    assert crisis_check("i want to kill myself")


def test_crisis_english_phrases():
    assert crisis_check("i can't go on anymore")
    assert crisis_check("i hurt myself last night")
    assert crisis_check("thinking about self harm")


def test_crisis_hinglish():
    assert crisis_check("yaar marna chahta hoon ab")
    assert crisis_check("jeena nahi chahta")
    assert crisis_check("khatam kar dunga sab")
    assert crisis_check("apne aap ko maar dunga")


def test_crisis_false_positive_killing_idiom_safe():
    assert not crisis_check("i could kill for a coffee")
    assert not crisis_check("that joke is killer")


def test_crisis_empty_input_safe():
    assert not crisis_check("")
    assert not crisis_check(None)


# ─── detect_concerns ─────────────────────────────────────
from therapist import detect_concerns, CONCERN_PATTERNS


def test_concern_work_matches_standalone():
    assert "work_stress" in detect_concerns("work pe boss bahut shout karta hai")


def test_concern_homework_does_not_leak_work():
    assert "work_stress" not in detect_concerns("homework finish karna hai, all good")


def test_concern_anxiety_hinglish():
    assert "anxiety" in detect_concerns("bahut ghabrahat ho rahi")


def test_concern_loneliness_akela_matches():
    assert "loneliness" in detect_concerns("bahut akela feel ho raha")


def test_concern_akela_does_not_leak_from_akelapan():
    assert "loneliness" not in detect_concerns("akelapan ek philosophical concept hai")


def test_concern_alone_does_not_leak_from_abalone():
    assert "loneliness" not in detect_concerns("ate abalone for dinner")


def test_concern_empty_input_returns_empty_list():
    assert detect_concerns("") == []
    assert detect_concerns(None) == []


def test_concern_multiple_can_match_same_message():
    cs = detect_concerns("work pressure aur insomnia se akela feel ho raha")
    assert "work_stress" in cs
    assert "sleep" in cs
    assert "loneliness" in cs


def test_all_concern_keys_have_compiled_pattern():
    expected_keys = {"work_stress","anxiety","relationship","sleep",
                     "loneliness","grief","self_esteem"}
    assert set(CONCERN_PATTERNS.keys()) == expected_keys


# ─── MOOD_COLORS / MOOD_EMOJI ────────────────────────────
from therapist import MOOD_COLORS, MOOD_EMOJI


def test_mood_colors_cover_all_valid_moods():
    assert set(MOOD_COLORS.keys()) == VALID_MOODS


def test_mood_emoji_cover_all_valid_moods():
    assert set(MOOD_EMOJI.keys()) == VALID_MOODS


def test_neutral_color_is_none():
    assert MOOD_COLORS["neutral"] is None


def test_sad_color_is_blue_hex():
    assert MOOD_COLORS["sad"] == "#38bdf8"


# ─── Profile schema v2 + migration ───────────────────────
import os
import json as _json
from pathlib import Path
import therapist as t

def test_default_profile_has_schema_v2():
    p = t._default_profile()
    assert p["schema"] == 2
    assert p["name"] == ""
    assert p["language_pref"] == "hinglish"
    assert p["concerns"] == []
    assert p["commitments"] == []
    assert p["session_summaries"] == []
    assert p["recurring_themes"] == []
    assert p["stats"] == {"total_messages": 0, "streak_days": 0, "last_active": ""}
    assert p["memory_paused"] is False


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    p = t._default_profile()
    p["name"] = "Abhinav"
    p["concerns"] = ["work_stress"]
    t.save_user("test_user", p)
    loaded = t.load_user("test_user")
    assert loaded["name"] == "Abhinav"
    assert loaded["concerns"] == ["work_stress"]


def test_save_uses_utf8_for_devanagari(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    p = t._default_profile()
    p["name"] = "अभिनव"
    t.save_user("test_user", p)
    raw = Path(t.get_profile_path("test_user")).read_text(encoding="utf-8")
    assert "अभिनव" in raw
    loaded = t.load_user("test_user")
    assert loaded["name"] == "अभिनव"


def test_load_missing_file_returns_default(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    p = t.load_user("missing_user")
    assert p["schema"] == 2
    assert p["name"] == ""




def test_corrupt_profile_returns_default(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    Path(t.get_profile_path("test_user")).write_text("not valid json {{{", encoding="utf-8")
    p = t.load_user("test_user")
    assert p["schema"] == 2
    assert p["name"] == ""


# ─── Memory mutations ───────────────────────────────────
def test_update_concerns_adds_new_unique(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    t.save_user("test_user", t._default_profile())
    t.update_concerns("test_user", "work pressure aur ghabrahat")
    p = t.load_user("test_user")
    assert "work_stress" in p["concerns"]
    assert "anxiety" in p["concerns"]
    t.update_concerns("test_user", "work pressure aur ghabrahat")
    p = t.load_user("test_user")
    assert p["concerns"].count("work_stress") == 1


def test_update_concerns_skipped_when_paused(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    p = t._default_profile()
    p["memory_paused"] = True
    t.save_user("test_user", p)
    t.update_concerns("test_user", "work pressure")
    assert t.load_user("test_user")["concerns"] == []


def test_clear_all_data_resets_to_default(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    p = t._default_profile()
    p["name"] = "Abhinav"
    p["concerns"] = ["work_stress"]
    t.save_user("test_user", p)
    t.clear_all_data("test_user")
    cleared = t.load_user("test_user")
    assert cleared["name"] == "Abhinav"
    assert cleared["concerns"] == []


def test_toggle_memory_pause_flips(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    t.save_user("test_user", t._default_profile())
    assert t.toggle_memory_pause("test_user") is True
    assert t.load_user("test_user")["memory_paused"] is True
    assert t.toggle_memory_pause("test_user") is False
    assert t.load_user("test_user")["memory_paused"] is False


# ─── Stats tracking ─────────────────────────────────────
from datetime import date, timedelta


def test_update_stats_first_use_starts_streak(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    t.save_user("test_user", t._default_profile())
    t.update_stats("test_user")
    p = t.load_user("test_user")
    assert p["stats"]["total_messages"] == 1
    assert p["stats"]["streak_days"] == 1
    assert p["stats"]["last_active"] == date.today().isoformat()


def test_update_stats_same_day_no_streak_change(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    t.save_user("test_user", t._default_profile())
    t.update_stats("test_user")
    t.update_stats("test_user")
    p = t.load_user("test_user")
    assert p["stats"]["total_messages"] == 2
    assert p["stats"]["streak_days"] == 1


def test_update_stats_consecutive_day_increments_streak(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    p = t._default_profile()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    p["stats"] = {"total_messages": 5, "streak_days": 3, "last_active": yesterday}
    t.save_user("test_user", p)
    t.update_stats("test_user")
    assert t.load_user("test_user")["stats"]["streak_days"] == 4


def test_update_stats_gap_resets_streak_to_one(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    p = t._default_profile()
    five_days_ago = (date.today() - timedelta(days=5)).isoformat()
    p["stats"] = {"total_messages": 10, "streak_days": 7, "last_active": five_days_ago}
    t.save_user("test_user", p)
    t.update_stats("test_user")
    assert t.load_user("test_user")["stats"]["streak_days"] == 1


# ─── System prompt ──────────────────────────────────────
from therapist import get_system_prompt


def test_system_prompt_contains_key_principles():
    sp = get_system_prompt("test_user")
    assert "empathetic" in sp
    assert "<mood>" in sp
    assert "iCall" in sp
    assert "Hinglish" in sp
    assert "BANNED" in sp.upper()


# ─── Helplines + client ─────────────────────────────────
from therapist import HELPLINES, get_client


def test_helplines_has_three_entries():
    assert len(HELPLINES) == 3
    names = {h["name"] for h in HELPLINES}
    assert names == {"iCall", "Vandrevala", "AASRA"}


def test_helplines_have_tel_links():
    for h in HELPLINES:
        assert h["tel"].startswith("tel:")
        assert h["num"]


def test_get_client_raises_clear_error_when_key_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as exc:
        get_client()
    assert "GROQ_API_KEY" in str(exc.value)


def test_get_client_returns_openai_when_key_present(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    c = get_client()
    assert c is not None
    assert "groq.com" in str(c.base_url)


# ─── therapist_agent (mocked) ───────────────────────────
from unittest.mock import MagicMock, patch
from therapist import therapist_agent


def _fake_stream(chunks: list[str]):
    """Build a fake openai stream iterator."""
    for c in chunks:
        m = MagicMock()
        m.choices = [MagicMock(delta=MagicMock(content=c))]
        yield m


def test_therapist_agent_yields_chunks_then_done(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_stream(
        ["<mood>sad</mood>\n", "Sun ke ", "dukh hua."]
    )
    with patch("therapist.get_client", return_value=fake_client):
        events = list(therapist_agent("test_user", "aaj sad hoon", chat_history=[]))

    assert events[0] == {"chunk": "<mood>sad</mood>\n", "done": False}
    assert events[-1]["done"] is True
    assert events[-1]["mood"] == "sad"
    assert events[-1]["reply"].strip() == "Sun ke dukh hua."
    assert events[-1]["crisis"] is False


def test_therapist_agent_passes_crisis_flag_in_user_msg(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_stream(
        ["<mood>sad</mood>\nSafe ho?"]
    )
    with patch("therapist.get_client", return_value=fake_client):
        list(therapist_agent("test_user", "kill myself", chat_history=[], in_crisis=True))

    sent = fake_client.chat.completions.create.call_args.kwargs["messages"]
    user_msg = sent[-1]["content"]
    assert "[CRISIS_DETECTED]" in user_msg


def test_therapist_agent_strips_current_msg_from_history(monkeypatch):
    """Bug fix #7: current msg must not appear twice."""
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_stream(
        ["<mood>neutral</mood>\nhi"]
    )
    history = [
        {"role": "user", "content": "old msg"},
        {"role": "assistant", "content": "old reply"},
        {"role": "user", "content": "current msg"},
    ]
    with patch("therapist.get_client", return_value=fake_client):
        list(therapist_agent("test_user", "current msg", chat_history=history))

    sent = fake_client.chat.completions.create.call_args.kwargs["messages"]
    assert len(sent) == 4
    assert sent[-1]["content"] == "current msg"
    prior_user_count = sum(1 for m in sent[1:-1] if m["role"] == "user" and m["content"] == "current msg")
    assert prior_user_count == 0


def test_therapist_agent_caps_history_at_ten(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_stream(["<mood>neutral</mood>\nhi"])
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(30)]
    history.append({"role": "user", "content": "current"})
    with patch("therapist.get_client", return_value=fake_client):
        list(therapist_agent("test_user", "current", chat_history=history))
    sent = fake_client.chat.completions.create.call_args.kwargs["messages"]
    assert len(sent) == 12


# ─── session_summary + commit_session_summary ───────────
def test_session_summary_returns_date_summary_themes_arc(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content=_json.dumps({
        "summary": "user vented about work",
        "mood_arc": ["anxious", "calm"],
        "themes": ["work_stress"],
    })))]
    fake_client.chat.completions.create.return_value = fake_resp
    history = [{"role": "user", "content": "work too much"},
               {"role": "assistant", "content": "<mood>anxious</mood>\nsamajh"}]
    with patch("therapist.get_client", return_value=fake_client):
        s = t.session_summary(history)
    assert s["summary"] == "user vented about work"
    assert s["mood_arc"] == ["anxious", "calm"]
    assert s["themes"] == ["work_stress"]
    assert s["date"] == date.today().isoformat()


def test_session_summary_filters_invalid_moods_and_themes(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content=_json.dumps({
        "summary": "", "mood_arc": ["anxious", "ecstatic"], "themes": ["work_stress", "alien"],
    })))]
    fake_client.chat.completions.create.return_value = fake_resp
    with patch("therapist.get_client", return_value=fake_client):
        s = t.session_summary([{"role": "user", "content": "x"}])
    assert s["mood_arc"] == ["anxious"]
    assert s["themes"] == ["work_stress"]


def test_session_summary_handles_invalid_json(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content="not json"))]
    fake_client.chat.completions.create.return_value = fake_resp
    with patch("therapist.get_client", return_value=fake_client):
        s = t.session_summary([{"role": "user", "content": "x"}])
    assert s["summary"] == ""
    assert s["mood_arc"] == []
    assert s["themes"] == []


def test_commit_session_summary_appends_and_caps_at_20(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    p = t._default_profile()
    p["session_summaries"] = [{"date": "2026-01-01", "summary": "old", "mood_arc": [], "themes": []}] * 20
    t.save_user("test_user", p)

    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content=_json.dumps({
        "summary": "new session", "mood_arc": ["calm"], "themes": ["sleep"],
    })))]
    fake_client.chat.completions.create.return_value = fake_resp
    with patch("therapist.get_client", return_value=fake_client):
        t.commit_session_summary("test_user", 
[{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"},
                                  {"role": "user", "content": "z"}, {"role": "assistant", "content": "w"}])
    p = t.load_user("test_user")
    assert len(p["session_summaries"]) == 20
    assert p["session_summaries"][-1]["summary"] == "new session"
    assert "sleep" in p["recurring_themes"]


def test_commit_session_summary_skipped_when_paused(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    p = t._default_profile()
    p["memory_paused"] = True
    t.save_user("test_user", p)
    t.commit_session_summary("test_user", 
[{"role": "user", "content": "x"}] * 4)
    assert t.load_user("test_user")["session_summaries"] == []


def test_commit_session_summary_skipped_for_short_chat(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    t.save_user("test_user", t._default_profile())
    t.commit_session_summary("test_user", 
[{"role": "user", "content": "hi"}])
    assert t.load_user("test_user")["session_summaries"] == []


# ─── update_profile ─────────────────────────────────────
def test_update_profile_sets_name_and_language(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    t.save_user("test_user", t._default_profile())
    t.update_profile("test_user", 
name="Abhinav", language_pref="english")
    p = t.load_user("test_user")
    assert p["name"] == "Abhinav"
    assert p["language_pref"] == "english"


def test_update_profile_preserves_existing_when_arg_none(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    p = t._default_profile()
    p["name"] = "X"
    p["language_pref"] = "hindi"
    t.save_user("test_user", p)
    t.update_profile("test_user", 
name=None, language_pref=None)
    after = t.load_user("test_user")
    assert after["name"] == "X"
    assert after["language_pref"] == "hindi"


# ─── Auth and Onboarding Tests ──────────────────────────

def test_signup_success_hashes_password_and_creates_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "USERS_DB_PATH", str(tmp_path / "users.json"))
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    
    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        success, msg = t.signup("newuser", "mypassword", "New User")
    
    assert success is True
    assert msg == "Success"
    
    db = t.load_users_db()
    assert "newuser" in db
    assert db["newuser"]["password"] != "mypassword"
    assert len(db["newuser"]["password"]) == 64  # SHA-256 length
    
    profile = t.load_user("newuser")
    assert profile["name"] == "New User"

def test_signup_fails_if_username_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "USERS_DB_PATH", str(tmp_path / "users.json"))
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    
    t.signup("existuser", "pass", "Name")
    success, msg = t.signup("existuser", "pass2", "Name2")
    assert success is False
    assert msg == "Username already exists."

def test_authenticate_success(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "USERS_DB_PATH", str(tmp_path / "users.json"))
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    
    t.signup("authuser", "securepass", "Auth User")
    assert t.authenticate("authuser", "securepass") is True

def test_authenticate_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "USERS_DB_PATH", str(tmp_path / "users.json"))
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    
    t.signup("failuser", "securepass", "Fail User")
    assert t.authenticate("failuser", "wrongpass") is False
    assert t.authenticate("wronguser", "securepass") is False

def test_onboarding_step_2_updates_concern(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    
    t.save_user("test_user", t._default_profile())
    resp = t.get_onboarding_response("test_user", 2, "💼 Work/Career")
    p = t.load_user("test_user")
    assert p["primary_concern"] == "work_stress"
    assert p["onboarding_step"] == 3

def test_onboarding_step_3_updates_style(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    
    t.save_user("test_user", t._default_profile())
    resp = t.get_onboarding_response("test_user", 3, "💡 Advice bhi chahiye")
    p = t.load_user("test_user")
    assert p["support_style"] == "advice_needed"
    assert p["onboarding_step"] == 4

def test_onboarding_step_4_updates_language(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    
    t.save_user("test_user", t._default_profile())
    resp = t.get_onboarding_response("test_user", 4, "🇬🇧 English")
    p = t.load_user("test_user")
    assert p["language_pref"] == "english"
    assert p["onboarding_step"] == 5
    assert p["onboarding_complete"] is True

def test_migrate_legacy_user(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    
    legacy_content = _json.dumps({"name": "Legacy", "stats": {"total_messages": 42}})
    legacy_file = tmp_path / "user_profile.json"
    legacy_file.write_text(legacy_content, encoding="utf-8")
    
    # We must patch legacy_path in migrate_legacy_user to point to our temp file
    # Or just run it in a temp dir using monkeypatch.chdir
    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        t.migrate_legacy_user("legacyuser")
    
    p = t.load_user("legacyuser")
    assert p["name"] == "Legacy"
    assert p["stats"]["total_messages"] == 42

def test_add_mood_log(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROFILES_DIR", str(tmp_path / "profiles"))
    if not os.path.exists(t.PROFILES_DIR): os.makedirs(t.PROFILES_DIR)
    
    username = "testuser"
    t.clear_all_data(username) # ensure clean state
    
    # Test adding log
    log = t.add_mood_log(
        username,
        date_str="2024-01-15",
        time_str="09:30",
        morning_score=4,
        tags=["anxious"],
        sleep_quality=3,
        one_word="heavy",
        from_chat=False,
        chat_mood_score=None
    )
    
    assert log["morningScore"] == 4
    
    user = t.load_user(username)
    assert len(user.get("mood_logs", [])) == 1
    assert user["mood_logs"][0]["tags"] == ["anxious"]

