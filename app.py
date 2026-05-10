import os
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from therapist import (
    therapist_agent, crisis_check, parse_mood,
    load_user, save_user, patch_profile, update_concerns, update_stats,
    commit_session_summary, clear_all_data, toggle_memory_pause,
    authenticate, signup, ONBOARDING_STEPS, get_onboarding_response,
    HELPLINES, MOOD_COLORS, MOOD_EMOJI, PERSONAS, add_mood_log
)

# ═══════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════
st.set_page_config(
    page_title="AbhiNova AI — AI Therapist",
    page_icon="🤗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Fail fast if API key missing (bug fix #13) ────────────
if not os.getenv("GROQ_API_KEY"):
    st.error("🔑 **GROQ_API_KEY missing.** Add it to `.env` and restart.\n\n"
             "Get a free key at https://console.groq.com")
    st.stop()

# ═══════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "chats" not in st.session_state:
    st.session_state.chats = {"💬 Chat 1": []}
    st.session_state.current_chat = "💬 Chat 1"
if "show_profile_setup" not in st.session_state:
    st.session_state.show_profile_setup = False

# ── chat_history + latest_mood available for sidebar (orb) and main area ──
chat_history = st.session_state.chats[st.session_state.current_chat]
latest_mood = "neutral"
for _c in reversed(chat_history):
    if _c["role"] == "assistant" and _c.get("mood"):
        latest_mood = _c["mood"]; break

# ═══════════════════════════════════════
# PREMIUM CSS — JARVIS THEME
# ═══════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Orbitron:wght@400;500;600;700;800;900&display=swap');

/* ── Global ── */
.stApp {
    background: linear-gradient(145deg, #020817 0%, #0a0f1f 30%, #0d1529 60%, #020817 100%);
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
}

/* ── Hide Streamlit branding but keep sidebar toggle ── */
#MainMenu, footer {visibility: hidden;}
.stDeployButton {display: none;}

/* Keep header visible for sidebar toggle but make it transparent */
header[data-testid="stHeader"] {
    background-color: transparent !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar {width: 6px;}
::-webkit-scrollbar-track {background: #0a0f1f;}
::-webkit-scrollbar-thumb {background: #1e3a5f; border-radius: 3px;}
::-webkit-scrollbar-thumb:hover {background: #38bdf8;}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020a1a 0%, #061225 100%) !important;
    border-right: 1px solid rgba(56, 189, 248, 0.15);
    box-shadow: 10px 0 30px rgba(0,0,0,0.5);
}


section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {
    color: #94a3b8;
    font-size: 0.88rem;
}

/* ── Buttons ── */
div.stButton > button {
    border-radius: 10px;
    border: 1px solid rgba(56, 189, 248, 0.3);
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.08), rgba(14, 165, 233, 0.04));
    color: #e2e8f0;
    padding: 8px 18px;
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 0.85rem;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
}

div.stButton > button:hover {
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.25), rgba(14, 165, 233, 0.15));
    border-color: #38bdf8;
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.2), 0 0 40px rgba(56, 189, 248, 0.05);
    transform: translateY(-1px);
    color: #fff;
}

/* ── Chat Messages ── */
[data-testid="stChatMessage"] {
    background: rgba(15, 23, 42, 0.4) !important;
    border: 1px solid rgba(56, 189, 248, 0.08);
    border-radius: 14px;
    padding: 16px !important;
    margin-bottom: 12px;
    backdrop-filter: blur(8px);
    will-change: transform, opacity;
    animation: msgFadeIn 0.3s ease-out;
}

@keyframes msgFadeIn {
    from {opacity: 0; transform: translateY(5px);}
    to {opacity: 1; transform: translateY(0);}
}

/* ── Chat Input — Definitive Dark Fix ── */
[data-testid="stBottom"], 
[data-testid="stBottomBlockContainer"] {
    background-color: #020817 !important;
}

/* Target the chat input container specifically */
[data-testid="stChatInput"] {
    background-color: #0f172a !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important;
    border-radius: 12px !important;
    box-shadow: 0 0 15px rgba(56, 189, 248, 0.1) !important;
}

/* Target the internal div and textarea */
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] textarea {
    background-color: #0f172a !important;
    color: #f8fafc !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #64748b !important;
}

/* Send button styling */
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #0ea5e9, #38bdf8) !important;
    border-radius: 8px !important;
    padding: 0 10px !important;
}


/* ── Premium Polish ── */
.jarvis-title {
    font-family: 'Orbitron', monospace;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: 2px;
}

.glass-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(56, 189, 248, 0.1);
    border-radius: 20px;
    padding: 24px;
    backdrop-filter: blur(10px);
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.glass-card:hover {
    transform: scale(1.02);
    border-color: rgba(56, 189, 248, 0.3);
}


.stat-value {
    font-family: 'Orbitron', monospace;
    color: #38bdf8;
    font-size: 1.5rem;
    font-weight: 700;
}

.stat-label {
    color: #64748b;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}


.greeting-sub {
    color: #64748b;
    font-size: 1.1rem;
    font-weight: 300;
    margin-top: 8px;
}


.action-card {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.6), rgba(30, 41, 59, 0.3));
    border: 1px solid rgba(56, 189, 248, 0.1);
    border-radius: 14px;
    padding: 16px 12px;
    text-align: center;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    animation: cardFloat 6s ease-in-out infinite;
}

.action-card:nth-child(1) { animation-delay: 0s; }
.action-card:nth-child(2) { animation-delay: 1s; }
.action-card:nth-child(3) { animation-delay: 2s; }

.action-card:hover {
    border-color: rgba(56, 189, 248, 0.5);
    box-shadow: 0 8px 30px rgba(56, 189, 248, 0.15), inset 0 0 30px rgba(56, 189, 248, 0.03);
    transform: translateY(-5px) scale(1.02);
}

@keyframes cardFloat {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-4px); }
}

.action-icon {
    font-size: 1.8rem;
    margin-bottom: 6px;
    animation: iconBounce 2s ease-in-out infinite;
}

@keyframes iconBounce {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}

.action-title {
    color: #e2e8f0;
    font-weight: 600;
    font-size: 0.85rem;
}

.action-desc {
    color: #64748b;
    font-size: 0.7rem;
    margin-top: 3px;
}

/* ── Greeting animation ── */
@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.greeting-text {
    font-family: 'Inter', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #38bdf8, #818cf8, #c084fc, #38bdf8);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    animation: gradientShift 4s ease infinite;
}

/* ── Fade-in stagger for home ── */
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.home-animated {
    animation: fadeSlideUp 0.6s ease-out forwards;
    opacity: 0;
}

.home-delay-1 { animation-delay: 0.1s; }
.home-delay-2 { animation-delay: 0.3s; }
.home-delay-3 { animation-delay: 0.5s; }

/* ── Suggestion chips ── */
.sugg-chip {
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.06), rgba(99, 102, 241, 0.06));
    border: 1px solid rgba(56, 189, 248, 0.15);
    border-radius: 24px;
    padding: 8px 16px;
    color: #94a3b8;
    font-size: 0.8rem;
    transition: all 0.3s ease;
    text-align: center;
}

.sugg-chip:hover {
    border-color: #38bdf8;
    color: #38bdf8;
    box-shadow: 0 0 15px rgba(56, 189, 248, 0.1);
}

/* ── Particles / ambient dots ── */
@keyframes float-particle {
    0%, 100% { transform: translateY(0px) translateX(0px); opacity: 0.3; }
    25% { transform: translateY(-15px) translateX(8px); opacity: 0.6; }
    50% { transform: translateY(-5px) translateX(-5px); opacity: 0.4; }
    75% { transform: translateY(-20px) translateX(3px); opacity: 0.7; }
}

.ambient-dots {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
}

.ambient-dot {
    position: absolute;
    width: 3px; height: 3px;
    background: rgba(56, 189, 248, 0.3);
    border-radius: 50%;
    animation: float-particle 8s ease-in-out infinite;
}

.sidebar-status {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.08));
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 10px;
    padding: 10px 14px;
    text-align: center;
    color: #6ee7b7;
    font-weight: 600;
    font-size: 0.85rem;
}

.orb-container {
    display: flex;
    justify-content: center;
    margin: 10px 0 5px 0;
}

.ai-orb {
    --mood-color: #38bdf8;
    --pulse-speed: 3s;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%,
        var(--mood-color),
        color-mix(in srgb, var(--mood-color) 50%, #0a0f1f),
        #1e3a5f);
    box-shadow: 0 0 30px var(--mood-color),
                0 0 60px color-mix(in srgb, var(--mood-color) 40%, transparent),
                inset 0 0 20px color-mix(in srgb, var(--mood-color) 30%, transparent);
    animation: orbPulse var(--pulse-speed) ease-in-out infinite;
}
.ai-orb.mood-sad      { --mood-color: #38bdf8; --pulse-speed: 5s; }
.ai-orb.mood-anxious  { --mood-color: #f59e0b; --pulse-speed: 1.5s; }
.ai-orb.mood-angry    { --mood-color: #ef4444; --pulse-speed: 1s; }
.ai-orb.mood-happy    { --mood-color: #10b981; --pulse-speed: 2.5s; }
.ai-orb.mood-lonely   { --mood-color: #a78bfa; --pulse-speed: 4s; }
.ai-orb.mood-calm     { --mood-color: #14b8a6; --pulse-speed: 6s; }
.ai-orb.mood-confused { --mood-color: #94a3b8; --pulse-speed: 2s; }
.ai-orb.mood-neutral  { --mood-color: #38bdf8; --pulse-speed: 3s; }

@keyframes orbPulse {
    0%, 100% { transform: scale(1); }
    50%      { transform: scale(1.05); }
}

/* ── Tier-2: msg-mood wrappers ───────────────── */
.msg-mood-wrap         { padding-left: 12px; border-left: 3px solid transparent; }
.msg-mood-sad          { border-left-color: #38bdf8; }
.msg-mood-anxious      { border-left-color: #f59e0b; }
.msg-mood-angry        { border-left-color: #ef4444; }
.msg-mood-happy        { border-left-color: #10b981; }
.msg-mood-lonely       { border-left-color: #a78bfa; }
.msg-mood-calm         { border-left-color: #14b8a6; }
.msg-mood-confused     { border-left-color: #94a3b8; }
.msg-mood-neutral      { border-left-color: transparent; padding-left: 0; }

/* ── Crisis card ─────────────────────────────── */
.crisis-card {
    border: 2px solid #ef4444;
    background: rgba(239, 68, 68, 0.08);
    border-radius: 14px;
    padding: 16px;
    margin: 12px 0;
    animation: crisisBreathe 4s ease-in-out infinite;
}
@keyframes crisisBreathe {
    0%, 100% { box-shadow: 0 0 8px rgba(239,68,68,0.2); }
    50%      { box-shadow: 0 0 24px rgba(239,68,68,0.4); }
}
.crisis-card a { color: #fca5a5; font-weight: 600; }
.crisis-card h3 { margin-top: 0; color: #fecaca; }

/* ── Streaming cursor ────────────────────────── */
.streaming-cursor {
    display: inline-block;
    margin-left: 2px;
    animation: cursorBlink 1s steps(1) infinite;
    color: #38bdf8;
}
@keyframes cursorBlink {
    0%, 50%   { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* ── Thinking dots ───────────────────────────── */
.thinking-dots {
    display: inline-flex; gap: 6px; align-items: center;
    padding: 4px 12px;
}
.thinking-dots span {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--mood-color, #38bdf8);
    animation: dotBounce var(--dot-speed, 1.4s) ease-in-out infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.15s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.3s; }
.thinking-dots.mood-sad      { --mood-color: #38bdf8; --dot-speed: 2.2s; }
.thinking-dots.mood-anxious  { --mood-color: #f59e0b; --dot-speed: 0.7s; }
.thinking-dots.mood-angry    { --mood-color: #ef4444; --dot-speed: 0.5s; }
.thinking-dots.mood-happy    { --mood-color: #10b981; --dot-speed: 1.0s; }
.thinking-dots.mood-lonely   { --mood-color: #a78bfa; --dot-speed: 1.8s; }
.thinking-dots.mood-calm     { --mood-color: #14b8a6; --dot-speed: 2.4s; }
.thinking-dots.mood-confused { --mood-color: #94a3b8; --dot-speed: 1.4s; }
.thinking-dots.mood-neutral  { --mood-color: #38bdf8; --dot-speed: 1.4s; }

@keyframes dotBounce {
    0%, 100% { transform: translateY(0); opacity: 0.5; }
    50%      { transform: translateY(-6px); opacity: 1; }
}

/* ── Ambient mood halo ───────────────────────── */
.ambient-halo {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background: radial-gradient(circle at 50% 30%,
        var(--halo-color, transparent) 0%, transparent 60%);
    opacity: 0.15;
    transition: background 4s ease;
}
.ambient-halo.mood-sad      { --halo-color: #38bdf8; }
.ambient-halo.mood-anxious  { --halo-color: #f59e0b; }
.ambient-halo.mood-angry    { --halo-color: #ef4444; }
.ambient-halo.mood-happy    { --halo-color: #10b981; }
.ambient-halo.mood-lonely   { --halo-color: #a78bfa; }
.ambient-halo.mood-calm     { --halo-color: #14b8a6; }
.ambient-halo.mood-confused { --halo-color: #94a3b8; }
.ambient-halo.mood-neutral  { --halo-color: transparent; }

/* ── Concerns + commitments ──────────────────── */
.concern-badge {
    display: inline-block;
    background: rgba(167, 139, 250, 0.1);
    border: 1px solid rgba(167, 139, 250, 0.25);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    color: #c4b5fd;
    margin: 2px 3px;
    text-transform: capitalize;
}
.commitment-item {
    background: rgba(20, 184, 166, 0.06);
    border-left: 3px solid #14b8a6;
    border-radius: 0 8px 8px 0;
    padding: 6px 10px;
    margin: 4px 0;
    font-size: 0.8rem;
    color: #99f6e4;
}

/* ── Glassmorphism upgrade (Task 26) ────────── */
section[data-testid="stSidebar"] div.stButton > button {
    backdrop-filter: blur(8px);
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.06), rgba(99, 102, 241, 0.04)) !important;
}
.stTextArea textarea, .stTextInput input {
    backdrop-filter: blur(8px);
    background: rgba(15, 23, 42, 0.5) !important;
}

.divider {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(56,189,248,0.2), transparent);
    margin: 16px 0;
}

.skill-badge {
    display: inline-block;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    color: #38bdf8;
    margin: 2px 3px;
}

.rec-item {
    background: rgba(99, 102, 241, 0.08);
    border-left: 3px solid #818cf8;
    border-radius: 0 8px 8px 0;
    padding: 8px 12px;
    margin: 6px 0;
    font-size: 0.82rem;
    color: #c4b5fd;
}

/* ── Spinner override ── */
.stSpinner > div {color: #38bdf8 !important;}

/* ── Columns gap fix ── */
[data-testid="stHorizontalBlock"] {gap: 12px;}

</style>
""", unsafe_allow_html=True)

# ── Ambient mood halo (Task 24) — Tier-2 Futurist UI ──
st.markdown(
    f'<div class="ambient-halo mood-{latest_mood}"></div>',
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════
# AUTHENTICATION UI
# ═══════════════════════════════════════
def login_signup_page():
    st.markdown("""
    <div style="text-align:center; padding: 40px 0;">
        <p class="jarvis-title" style="font-size:2.5rem;">ABHINOVA AI</p>
        <p style="color:#94a3b8; font-size:1.2rem;">Empathetic AI Therapist</p>
    </div>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs(["🔐 Login", "📝 Signup"])
    
    with tabs[0]:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            if submit:
                if authenticate(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
                    
    with tabs[1]:
        with st.form("signup_form"):
            new_name = st.text_input("Your Name")
            new_user = st.text_input("Choose Username")
            new_pass = st.text_input("Choose Password", type="password")
            submit = st.form_submit_button("Create Account", use_container_width=True)
            if submit:
                if not new_name or not new_user or not new_pass:
                    st.warning("Please fill all fields")
                else:
                    success, msg = signup(new_user, new_pass, new_name)
                    if success:
                        st.success("Account created! Please login.")
                    else:
                        st.error(msg)

if not st.session_state.logged_in:
    login_signup_page()
    st.stop()

username = st.session_state.username

# ═══════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════
def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    elif hour < 21:
        return "Good Evening"
    return "Good Night"


def get_greeting_emoji():
    hour = datetime.now().hour
    if hour < 12:
        return "☀️"
    elif hour < 17:
        return "🌤️"
    elif hour < 21:
        return "🌅"
    return "🌙"


# ═══════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════
user = load_user(username)
user_name = user.get("name") or "User"
stats = user.get("stats", {})

# AI Orb
st.sidebar.markdown(f"""
<div class="orb-container"><div class="ai-orb mood-{latest_mood}"></div></div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div style="text-align:center; margin-bottom:8px;">
    <p class="jarvis-title" style="font-size:1.2rem;">ABHINOVA AI</p>
    <p class="jarvis-sub">Empathetic AI Therapist</p>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Persona Selection ──
st.sidebar.markdown("#### 🎭 Choose Persona")
current_persona = user.get("persona", "dost")

for p_key, p_val in PERSONAS.items():
    is_active = p_key == current_persona
    btn_label = f"✅ {p_val['name']}" if is_active else p_val['name']
    if st.sidebar.button(btn_label, key=f"p_{p_key}", use_container_width=True, help=p_val['description']):
        update_profile(username, persona=p_key)
        st.toast(f"Persona switched to {p_val['name']}")
        st.rerun()

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Stats Row ──
s1, s2 = st.sidebar.columns(2)
with s1:
    st.markdown(f'<div style="text-align:center"><div class="stat-value">{stats.get("total_messages", 0)}</div><div class="stat-label">Messages</div></div>', unsafe_allow_html=True)
with s2:
    st.markdown(f'<div style="text-align:center"><div class="stat-value">🔥{stats.get("streak_days", 0)}</div><div class="stat-label">Streak</div></div>', unsafe_allow_html=True)

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Chat Management ──
st.sidebar.markdown("#### 💬 Conversations")

if st.sidebar.button("➕ New Chat", use_container_width=True):
    idx = len(st.session_state.chats) + 1
    new_chat = f"💬 Chat {idx}"
    st.session_state.chats[new_chat] = []
    st.session_state.current_chat = new_chat
    st.rerun()

for chat_name in list(st.session_state.chats.keys()):
    is_active = chat_name == st.session_state.current_chat
    label = f"▸ {chat_name}" if is_active else chat_name
    if st.sidebar.button(label, key=f"chat_{chat_name}", use_container_width=True):
        st.session_state.current_chat = chat_name
        st.rerun()

col_del, col_export = st.sidebar.columns(2)
with col_del:
    if st.button("🗑️ Delete", use_container_width=True):
        if len(st.session_state.chats) > 1:
            del st.session_state.chats[st.session_state.current_chat]
            st.session_state.current_chat = list(st.session_state.chats.keys())[0]
        else:
            st.session_state.chats[st.session_state.current_chat] = []
        st.rerun()

with col_export:
    if st.button("📋 Export", use_container_width=True):
        chat_data = st.session_state.chats[st.session_state.current_chat]
        if chat_data:
            md = f"# {st.session_state.current_chat}\n\n"
            for msg in chat_data:
                role = "🤖 AbhiNova" if msg["role"] == "assistant" else "👤 You"
                md += f"### {role}\n{msg['content']}\n\n---\n\n"
            st.sidebar.download_button("⬇️ Download", md, "chat_export.md", "text/markdown", use_container_width=True)
        else:
            st.sidebar.info("No messages to export")

# ── End session (writes a summary to memory) ──
if st.sidebar.button("✅ End session", use_container_width=True, key="end_session"):
    chat_data = st.session_state.chats[st.session_state.current_chat]
    if len(chat_data) >= 4:
        with st.spinner("Saving summary…"):
            try:
                commit_session_summary(username, chat_data)
                st.toast("Session summary saved.", icon="💾")
            except Exception as e:
                st.toast(f"Couldn't save summary: {e}", icon="⚠️")
    st.session_state.chats[st.session_state.current_chat] = []
    st.rerun()

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Profile Section ──
st.sidebar.markdown("#### 👤 Profile")

if user.get("name"):
    st.sidebar.markdown(f"**{user['name']}**")

# Profile edit (v2 schema: name + language_pref)
with st.sidebar.expander("✏️ Edit Profile"):
    new_name = st.text_input("Name", value=user.get("name", ""), key="pname")
    lang_options = ["hinglish", "english", "hindi"]
    new_lang = st.selectbox(
        "Preferred language",
        options=lang_options,
        index=lang_options.index(user.get("language_pref", "hinglish")),
        key="plang",
    )
    if st.button("💾 Save Profile", use_container_width=True):
        patch_profile(username, name=new_name, language_pref=new_lang)
        st.rerun()

# ── 🌱 Concerns badges ────────────────────────────
concerns = user.get("concerns", [])
if concerns:
    badges = " ".join([f'<span class="concern-badge">{c.replace("_", " ")}</span>' for c in concerns[:8]])
    st.sidebar.markdown(f"<div style='margin:8px 0'>{badges}</div>", unsafe_allow_html=True)

# ── 📝 Commitments preview (top 3 pending) ────────
pending = [c for c in user.get("commitments", []) if not c.get("done")]
if pending:
    st.sidebar.markdown("#### 📝 Commitments")
    for c in pending[:3]:
        st.sidebar.markdown(
            f'<div class="commitment-item">⬜ {c.get("task","")}</div>',
            unsafe_allow_html=True,
        )

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── 🔒 Privacy panel ──────────────────────────────
with st.sidebar.expander("🔒 Privacy"):
    paused_now = user.get("memory_paused", False)
    st.caption(
        "What's stored: name, concerns, last 20 session **summaries** (not raw chats), "
        "mood arc, recurring themes, streak count. All local in `user_profile.json`."
    )
    if st.button(("▶ Resume memory" if paused_now else "⏸ Pause memory this session"),
                 use_container_width=True, key="btn_pause_mem"):
        toggle_memory_pause(username)
        st.rerun()
    if st.button("🗑 Clear all my data", use_container_width=True, key="btn_clear_data"):
        st.session_state["confirm_clear"] = True
    if st.session_state.get("confirm_clear"):
        st.warning("Sure? This wipes name, concerns, summaries, todos, stats.")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("Yes, wipe", use_container_width=True, key="btn_wipe_yes"):
                clear_all_data(username)
                st.session_state["confirm_clear"] = False
                st.rerun()
        with cc2:
            if st.button("Cancel", use_container_width=True, key="btn_wipe_no"):
                st.session_state["confirm_clear"] = False
                st.rerun()

# ── ⚙️ Features Settings ──────────────────────────
with st.sidebar.expander("⚙️ Settings"):
    settings = user.get("settings", {})
    
    mood_on = st.toggle("Mood Tracker", value=settings.get("mood_tracker", True))
    typing_on = st.toggle("Typing Animation", value=settings.get("typing_animation", True))
    halo_on = st.toggle("Ambient Halo", value=settings.get("ambient_halo", True))
    
    if mood_on != settings.get("mood_tracker") or \
       typing_on != settings.get("typing_animation") or \
       halo_on != settings.get("ambient_halo"):
        user["settings"] = {
            "mood_tracker": mood_on,
            "typing_animation": typing_on,
            "ambient_halo": halo_on,
            "privacy_pause": settings.get("privacy_pause", False)
        }
        save_user(username, user)
        st.rerun()

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)
st.sidebar.markdown(f"""
<div class="sidebar-status">
    ⚡ AbhiNova AI — Online
</div>
""", unsafe_allow_html=True)

# ── Persistent disclaimer (Task 27) ──
st.sidebar.markdown("""
<div style="margin-top:14px; padding:10px 12px; border:1px solid rgba(148,163,184,0.2);
            border-radius:10px; background:rgba(15,23,42,0.4); font-size:0.72rem;
            color:#94a3b8; line-height:1.4;">
    ⚠️ AbhiNova is <strong>not</strong> a licensed therapist.
    In emergencies call <a href="tel:9152987821" style="color:#fca5a5;">iCall: 9152987821</a>.
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# MAIN HEADER
# ═══════════════════════════════════════
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown(f'<p class="jarvis-title">🤖 ABHINOVA AI</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="jarvis-sub">Personal Intelligence System • Always Ready</p>', unsafe_allow_html=True)
with h2:
    st.markdown(f"""
    <div style="text-align:right; padding-top:8px;">
        <span style="color:#64748b; font-size:0.8rem;">{datetime.now().strftime("%B %d, %Y • %I:%M %p")}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ═══════════════════════════════════════
# HOME SCREEN (when chat is empty)
# ═══════════════════════════════════════
if len(chat_history) == 0:

    # Ambient floating particles (Reduced for performance)
    import random
    dots_html = '<div class="ambient-dots">'
    for i in range(8):
        x = random.randint(5, 95)
        y = random.randint(5, 95)
        delay = round(random.uniform(0, 5), 1)
        size = random.choice([2, 3])
        dots_html += f'<div class="ambient-dot" style="left:{x}%;top:{y}%;animation-delay:{delay}s;width:{size}px;height:{size}px;"></div>'
    dots_html += '</div>'
    st.markdown(dots_html, unsafe_allow_html=True)

    # Greeting with animation
    st.markdown(f"""
    <div class="home-animated home-delay-1" style="text-align:center; padding:20px 0 8px 0;">
        <p style="font-size:2.5rem; margin:0;">{get_greeting_emoji()}</p>
        <p class="greeting-text">{get_greeting()}, {user_name}</p>
        <p class="greeting-sub">Aaj kaisa feel kar rahe ho?</p>
    </div>
    """, unsafe_allow_html=True)

    # Mood quick-start buttons — pre-fill input on click
    st.markdown("""<div class="home-animated home-delay-2">
        <p style='text-align:center; color:#475569; font-size:0.75rem; letter-spacing:2px; text-transform:uppercase; margin:16px 0 8px 0;'>💬 Start with a feeling</p>
    </div>""", unsafe_allow_html=True)

    mood_templates = {
        "😔 Sad":         "Aaj sad feel ho raha hai. ",
        "😰 Anxious":     "Bahut ghabrahat ho rahi hai. ",
        "😤 Frustrated":  "Bahut frustrated hoon. ",
        "😐 Numb":        "Kuch feel hi nahi ho raha. ",
        "💬 Just talk":   "",
    }
    mb_cols = st.columns(5)
    for i, (label, template) in enumerate(mood_templates.items()):
        with mb_cols[i]:
            if st.button(label, key=f"mood_{i}", use_container_width=True):
                st.session_state["prefill_input"] = template
                st.rerun()


# ═══════════════════════════════════════
# CRISIS CARD HELPER (hardcoded — never LLM-generated)
# ═══════════════════════════════════════
def render_crisis_card():
    helpline_html = "".join(
        f'<p>📞 <a href="{h["tel"]}">{h["name"]}: {h["num"]}</a></p>'
        for h in HELPLINES
    )
    st.markdown(f"""
    <div class="crisis-card">
      <h3>🆘 Main sun raha hoon — tum safe raho.</h3>
      <p><strong>Helplines (24×7, free, India):</strong></p>
      {helpline_html}
      <p><em>Tum akele nahi ho. Kya tum abhi safe ho?</em></p>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════
# DISPLAY CHAT MESSAGES (with mood-bordered wrapper)
# ═══════════════════════════════════════
for chat in chat_history:
    role = chat["role"]
    mood = chat.get("mood", "neutral") if role == "assistant" else None
    emoji = MOOD_EMOJI.get(mood, "") if mood else ""
    avatar = f"🤖{emoji}" if role == "assistant" else "👤"
    with st.chat_message(role, avatar=avatar):
        if mood and mood != "neutral":
            st.markdown(
                f'<div class="msg-mood-wrap msg-mood-{mood}">{chat["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(chat["content"])


# ═══════════════════════════════════════
# AUTO AI RESPONSE (streaming therapist agent)
# ═══════════════════════════════════════
if chat_history:
    last_msg = chat_history[-1]

    if last_msg["role"] == "user" and "processed" not in last_msg:
        user_input = last_msg["content"]

        # Latest assistant mood — drives thinking-dot color
        latest_mood = "neutral"
        for c in reversed(chat_history[:-1]):
            if c["role"] == "assistant" and c.get("mood"):
                latest_mood = c["mood"]; break

        # ── Crisis check (deterministic, BEFORE LLM call) ──
        in_crisis = crisis_check(user_input)
        if in_crisis:
            render_crisis_card()

        # ── Profile updates (silent) ──
        update_concerns(username, user_input)
        update_stats(username)

        # ── Stream LLM response ──
        mood = "neutral"
        full_reply = ""
        full_raw = ""
        with st.chat_message("assistant", avatar="🤖"):
            placeholder = st.empty()
            placeholder.markdown(
                f'<div class="thinking-dots mood-{latest_mood}">'
                '<span></span><span></span><span></span></div>',
                unsafe_allow_html=True,
            )
            
            # Slower typing feel (Task 31)
            import time
            time.sleep(1.5) 
            
            try:
                for evt in therapist_agent(username, user_input, chat_history, in_crisis=in_crisis):
                    if evt["done"]:
                        mood = evt["mood"]
                        full_reply = evt["reply"]
                        placeholder.markdown(
                            f'<div class="msg-mood-wrap msg-mood-{mood}">{full_reply}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        full_raw += evt["chunk"]
                        _, display, _ = parse_mood(full_raw)
                        placeholder.markdown(
                            f'<div class="msg-mood-wrap msg-mood-{latest_mood}">'
                            f'{display}<span class="streaming-cursor">▊</span></div>',
                            unsafe_allow_html=True,
                        )
                        # Micro-delay for "human" stream speed
                        time.sleep(0.02)
            except Exception as e:
                placeholder.markdown(f"⚠️ Kuch issue hua: {e}\n\nPlease retry.")
                mood = "neutral"
                full_reply = ""

        # Bug fix #11: mark processed AFTER successful generation
        last_msg["processed"] = True
        chat_history.append({
            "role": "assistant",
            "content": full_reply or "⚠️ Couldn't generate a response. Try again?",
            "mood": mood,
        })
        st.rerun()

# ── Onboarding Overlay ──
if not user.get("onboarding_complete") and len(chat_history) == 0:
    step = user.get("onboarding_step", 1)
    onboard_data = ONBOARDING_STEPS.get(step)
    
    if onboard_data:
        msg = onboard_data['message']
        if step == 1:
            msg = f"Hey {user_name}! {msg}"
            
        st.markdown(f"""
        <div class="glass-card home-animated" style="margin-top:20px;">
            <p style="font-size:1.1rem; line-height:1.6;">{msg}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if "options" in onboard_data:
            # Display options as buttons
            cols = st.columns(len(onboard_data["options"]))
            for i, opt in enumerate(onboard_data["options"]):
                with cols[i % len(cols)]:
                    if st.button(opt, key=f"onb_{step}_{i}", use_container_width=True):
                        get_onboarding_response(username, step, opt)
                        st.rerun()
        st.stop()


# ═══════════════════════════════════════
# CHAT INPUT (with prefill from mood buttons)
# ═══════════════════════════════════════
prefill = st.session_state.pop("prefill_input", "")
if prefill:
    with st.container():
        edited = st.text_area("✍️ Edit and send:", value=prefill, key="prefill_edit", height=80)
        col_send, col_cancel = st.columns([1, 1])
        with col_send:
            if st.button("Send", use_container_width=True, key="prefill_send"):
                if edited.strip():
                    chat_history.append({"role": "user", "content": edited.strip()})
                    st.rerun()
        with col_cancel:
            if st.button("Cancel", use_container_width=True, key="prefill_cancel"):
                st.rerun()
else:
    user_input = st.chat_input("Ask AbhiNova anything...")
    if user_input:
        chat_history.append({"role": "user", "content": user_input})
        st.rerun()
        </div>
        """, unsafe_allow_html=True)
        
        if "options" in onboard_data:
            # Display options as buttons
            cols = st.columns(len(onboard_data["options"]))
            for i, opt in enumerate(onboard_data["options"]):
                with cols[i % len(cols)]:
                    if st.button(opt, key=f"onb_{step}_{i}", use_container_width=True):
                        get_onboarding_response(username, step, opt)
                        st.rerun()
        st.stop()


# ═══════════════════════════════════════
# CHAT INPUT (with prefill from mood buttons)
# ═══════════════════════════════════════
prefill = st.session_state.pop("prefill_input", "")
if prefill:
    with st.container():
        edited = st.text_area("✍️ Edit and send:", value=prefill, key="prefill_edit", height=80)
        col_send, col_cancel = st.columns([1, 1])
        with col_send:
            if st.button("Send", use_container_width=True, key="prefill_send"):
                if edited.strip():
                    chat_history.append({"role": "user", "content": edited.strip()})
                    st.rerun()
        with col_cancel:
            if st.button("Cancel", use_container_width=True, key="prefill_cancel"):
                st.rerun()
else:
    user_input = st.chat_input("Ask AbhiNova anything...")
    if user_input:
        chat_history.append({"role": "user", "content": user_input})
        st.rerun()