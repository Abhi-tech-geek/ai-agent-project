import os
import uuid
import streamlit as st
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import streamlit.components.v1 as components

load_dotenv()

from therapist import (
    therapist_agent, crisis_check, parse_mood,
    load_user, save_user, patch_profile, update_concerns, update_stats,
    commit_session_summary, clear_all_data, toggle_memory_pause,
    authenticate, signup, ONBOARDING_STEPS, get_onboarding_response,
    HELPLINES, MOOD_COLORS, MOOD_EMOJI, PERSONAS, add_mood_log,
    get_dashboard_stats, check_achievements, delete_session_summary,
    normalize_session_summary, should_offer_session_summary,
    # Phase 4
    journal_generate_questions, journal_identify_distortion,
    journal_generate_reframe, add_journal_entry, get_journal_entries,
    delete_journal_entry, get_journal_stats, DISTORTION_LABELS,
    MOOD_TO_MUSIC, music_for_mood, add_music_feedback,
    consecutive_sad_messages, export_user_data, clear_feature_data,
    update_profile,
)
import json
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

COMPONENT_DIR = Path(__file__).parent / "components" / "voice_phase3"
voice_component = components.declare_component("voice_phase3", path=str(COMPONENT_DIR))

MUSIC_COMPONENT_DIR = Path(__file__).parent / "components" / "music_player"
music_component = components.declare_component("music_player", path=str(MUSIC_COMPONENT_DIR))

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
if "chat_started_at" not in st.session_state:
    st.session_state.chat_started_at = {}
if "summary_offer" not in st.session_state:
    st.session_state.summary_offer = None
if "summary_offer_seen" not in st.session_state:
    st.session_state.summary_offer_seen = []
if "component_event_id" not in st.session_state:
    st.session_state.component_event_id = None
if "input_nonce" not in st.session_state:
    st.session_state.input_nonce = 0
if "last_activity_at" not in st.session_state:
    st.session_state.last_activity_at = datetime.now().isoformat()

st.session_state.chat_started_at.setdefault(
    st.session_state.current_chat,
    datetime.now().isoformat(),
)

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
    background: #020817;
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
    overflow-x: hidden;
}

/* ── Holographic Scanlines Overlay ── */
.stApp::before {
    content: " ";
    position: fixed;
    top: 0; left: 0; width: 100%; height: 100%;
    background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%), 
                linear-gradient(90deg, rgba(255, 0, 0, 0.02), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.02));
    background-size: 100% 3px, 3px 100%;
    z-index: 1000;
    pointer-events: none;
    opacity: 0.3;
}

/* ── Hide Streamlit branding but keep sidebar toggle ── */
#MainMenu, footer {visibility: hidden;}
.stDeployButton {display: none;}

/* Keep header visible for sidebar toggle but make it transparent */
header[data-testid="stHeader"] {
    background-color: transparent !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar {width: 4px;}
::-webkit-scrollbar-track {background: transparent;}
::-webkit-scrollbar-thumb {background: rgba(56, 189, 248, 0.2); border-radius: 10px;}
::-webkit-scrollbar-thumb:hover {background: #38bdf8;}

/* ── Sidebar (Diagnostics Panel) ── */
section[data-testid="stSidebar"] {
    background: rgba(2, 10, 26, 0.95) !important;
    border-right: 1px solid rgba(56, 189, 248, 0.2);
    backdrop-filter: blur(20px);
}

/* ── Buttons (Neural Interface Style) ── */
div.stButton > button {
    border-radius: 4px;
    border: 1px solid rgba(56, 189, 248, 0.4);
    background: rgba(15, 23, 42, 0.6);
    color: #38bdf8;
    padding: 10px 20px;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.75rem;
    letter-spacing: 1px;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(10px);
    text-transform: uppercase;
}

div.stButton > button:hover {
    background: rgba(56, 189, 248, 0.15);
    border-color: #38bdf8;
    box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
    color: #fff;
    transform: translateX(4px);
}

/* ── Chat Messages (Floating Data Packets) ── */
[data-testid="stChatMessage"] {
    background: rgba(15, 23, 42, 0.3) !important;
    border: 1px solid rgba(56, 189, 248, 0.1);
    border-radius: 0px 12px 12px 12px;
    padding: 14px !important;
    margin-bottom: 16px;
    backdrop-filter: blur(12px);
    box-shadow: 5px 5px 15px rgba(0,0,0,0.2);
    animation: msgSlideIn 0.5s cubic-bezier(0.23, 1, 0.32, 1);
}

@keyframes msgSlideIn {
    from {opacity: 0; transform: translateX(-10px) scale(0.98);}
    to {opacity: 1; transform: translateX(0) scale(1);}
}

/* ── Holographic Panel Animation ── */
.hologram-panel {
    animation: panelSlideIn 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    background: rgba(10, 25, 47, 0.7);
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 15px;
    padding: 25px;
    backdrop-filter: blur(25px);
    box-shadow: 0 0 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(56, 189, 248, 0.05);
}

@keyframes panelSlideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

/* ── Reactive Distress Palette ── */
.distress-mode {
    --halo-color: #14b8a6 !important; /* Calming Teal */
    --accent-color: #38bdf8;
    background: radial-gradient(circle at 50% 50%, rgba(20, 184, 166, 0.05) 0%, #020817 100%) !important;
}

/* ── Premium Polish ── */
.jarvis-title {
    font-family: 'Orbitron', sans-serif;
    color: #38bdf8;
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: 4px;
    text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
}

.glass-card {
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(56, 189, 248, 0.15);
    border-radius: 12px;
    padding: 20px;
    backdrop-filter: blur(15px);
}

.stat-value {
    font-family: 'Orbitron', monospace;
    color: #38bdf8;
    font-size: 1.4rem;
    text-shadow: 0 0 5px rgba(56, 189, 248, 0.5);
}

.stat-label {
    color: #64748b;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 2px;
}

/* ── AI Orb Refactoring ── */
.orb-container {
    position: relative;
    display: flex;
    justify-content: center;
    margin: 20px 0;
}

.ai-orb {
    --mood-color: #38bdf8;
    width: 90px;
    height: 90px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #fff, var(--mood-color) 40%, #020817 90%);
    box-shadow: 0 0 20px var(--mood-color), 0 0 40px var(--mood-color), inset 0 0 15px rgba(255,255,255,0.5);
    animation: orbFloat 4s ease-in-out infinite;
}

@keyframes orbFloat {
    0%, 100% { transform: translateY(0) scale(1); filter: brightness(1); }
    50% { transform: translateY(-10px) scale(1.05); filter: brightness(1.2); }
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
    # Ambient particles for login
    import random
    dots_html = '<div class="ambient-dots">'
    for i in range(12):
        x, y = random.randint(0, 100), random.randint(0, 100)
        delay, size = round(random.uniform(0, 8), 1), random.choice([2, 3])
        dots_html += f'<div class="ambient-dot" style="left:{x}%;top:{y}%;animation-delay:{delay}s;width:{size}px;height:{size}px;background:rgba(56,189,248,0.25);"></div>'
    dots_html += '</div>'
    st.markdown(dots_html, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; padding: 40px 0 10px 0;">
        <div class="orb-container"><div class="ai-orb" style="width:100px; height:100px; box-shadow: 0 0 40px rgba(56,189,248,0.3);"></div></div>
        <p class="jarvis-title" style="font-size:2.8rem; margin-top:15px; letter-spacing:8px;">ABHINOVA</p>
        <p style="color:#64748b; font-size:0.85rem; letter-spacing:2px; text-transform:uppercase; margin-top:-10px;">Your Personal Intelligence Core</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_l, col_main, col_r = st.columns([1, 1.8, 1])
    
    with col_main:
        st.markdown('<div class="glass-card" style="padding:30px; border-radius:15px;">', unsafe_allow_html=True)
        tabs = st.tabs(["🔐 Login", "👤 Sign Up"])
        
        with tabs[0]:
            username = st.text_input("Username", placeholder="Enter your username...")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            if st.button("Enter Neural Link", use_container_width=True):
                if not username or not password:
                    st.error("Please enter both username and password")
                elif authenticate(username, password):
                    with st.spinner("Authenticating..."):
                        import time
                        time.sleep(0.8)
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
                        
        with tabs[1]:
            new_name = st.text_input("Full Name", placeholder="Your name...")
            new_user = st.text_input("New Username", placeholder="Choose a username...")
            new_pass = st.text_input("New Password", type="password", placeholder="••••••••")
            
            if st.button("Create Neural Profile", use_container_width=True):
                if not new_name or not new_user or not new_pass:
                    st.warning("Please fill in all fields")
                else:
                    success, msg = signup(new_user, new_pass, new_name)
                    if success:
                        st.success("Profile registered! You can now login.")
                    else:
                        st.error(f"Error: {msg}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; margin-top:30px; font-size:0.7rem; color:#475569; opacity:0.6;">
        <p>AES-256 SECURED | V4.2.0 STABLE</p>
    </div>
    """, unsafe_allow_html=True)

if not st.session_state.logged_in:
    login_signup_page()
    st.stop()

username = st.session_state.username

@st.dialog("Daily Check-in")
def mood_checkin_dialog():
    st.write("How are you feeling today?")
    score = st.slider("Mood Score", 1, 10, 5, format="Score: %d")
    
    tags = st.multiselect(
        "Emotions",
        ["Anxious", "Tired", "Frustrated", "Numb", "Confused", "Motivated", "Content", "Sad"]
    )
    
    sleep = st.radio("Sleep Quality", [1, 2, 3, 4, 5], index=2, horizontal=True)
    word = st.text_input("One word for today:")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Skip for now", use_container_width=True):
            st.session_state["mood_checked_today"] = True
            st.rerun()
    with col2:
        if st.button("Log Mood", type="primary", use_container_width=True):
            add_mood_log(
                st.session_state.username,
                date_str=datetime.now().strftime("%Y-%m-%d"),
                time_str=datetime.now().strftime("%H:%M"),
                morning_score=score,
                tags=tags,
                sleep_quality=sleep,
                one_word=word
            )
            new_achievements = check_achievements(st.session_state.username)
            for ach in new_achievements:
                st.toast(f"Achievement Unlocked: {ach} 🏆", icon="🌟")
            st.session_state["mood_checked_today"] = True
            st.toast("Mood logged successfully!", icon="✅")
            st.rerun()

if "mood_checked_today" not in st.session_state:
    st.session_state["mood_checked_today"] = False

today_str = datetime.now().strftime("%Y-%m-%d")
user_data = load_user(username)
logs = user_data.get("mood_logs", [])
has_log_today = any(l.get("date") == today_str for l in logs)

if not has_log_today and not st.session_state["mood_checked_today"]:
    mood_checkin_dialog()


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


SUMMARY_PROMPT_TEXT = (
    "Should I put together a quick summary of what we talked about today?"
)


def consume_component_event(event):
    if not event or not isinstance(event, dict):
        return None
    event_id = event.get("eventId")
    if not event_id or event_id == st.session_state.component_event_id:
        return None
    st.session_state.component_event_id = event_id
    return event


def get_voice_language(user_data, settings):
    choice = settings.get("recognition_language", "auto")
    if choice == "hi":
        return "hi-IN"
    if choice == "en":
        return "en-US"
    return "hi-IN" if user_data.get("language_pref") == "hindi" else "en-US"


def current_duration_minutes():
    started = st.session_state.chat_started_at.get(st.session_state.current_chat)
    try:
        start_dt = datetime.fromisoformat(started)
    except (TypeError, ValueError):
        start_dt = datetime.now()
    return max(0, int((datetime.now() - start_dt).total_seconds() // 60))


def real_messages(messages):
    return [m for m in messages if not m.get("summary_prompt")]


def append_message(role, content, **extra):
    msg = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    msg.update(extra)
    chat_history.append(msg)
    return msg


def clear_current_chat():
    st.session_state.chats[st.session_state.current_chat] = []
    st.session_state.chat_started_at[st.session_state.current_chat] = datetime.now().isoformat()
    st.session_state.summary_offer = None
    st.session_state.input_nonce += 1


def open_summary_offer(reason, clear_after=False):
    offer = st.session_state.get("summary_offer")
    if offer and offer.get("chat") == st.session_state.current_chat:
        return
    st.session_state.summary_offer = {
        "chat": st.session_state.current_chat,
        "reason": reason,
        "clear_after": clear_after,
    }
    if not chat_history or not chat_history[-1].get("summary_prompt"):
        append_message(
            "assistant",
            SUMMARY_PROMPT_TEXT,
            mood="calm",
            summary_prompt=True,
        )


def maybe_offer_message_count_summary():
    seen = set(st.session_state.get("summary_offer_seen", []))
    chat_key = st.session_state.current_chat
    if chat_key in seen or st.session_state.get("summary_offer"):
        return
    if len(real_messages(chat_history)) >= 10:
        seen.add(chat_key)
        st.session_state.summary_offer_seen = list(seen)
        open_summary_offer("message_count", clear_after=False)


def maybe_offer_inactivity_summary():
    if st.session_state.get("summary_offer") or len(real_messages(chat_history)) < 4:
        return
    try:
        last_dt = datetime.fromisoformat(st.session_state.last_activity_at)
    except (TypeError, ValueError):
        last_dt = datetime.now()
    inactive_minutes = (datetime.now() - last_dt).total_seconds() / 60
    if inactive_minutes >= 30:
        open_summary_offer("inactive", clear_after=True)


def handle_user_text(text, source="typed"):
    text = (text or "").strip()
    if not text:
        return
    st.session_state.last_activity_at = datetime.now().isoformat()
    closing = should_offer_session_summary(text)
    append_message("user", text, source=source, processed=closing)
    if closing:
        open_summary_offer("closing_phrase", clear_after=True)
    st.session_state.input_nonce += 1
    st.rerun()


def finish_summary_offer(generate_summary):
    offer = st.session_state.get("summary_offer") or {}
    clear_after = offer.get("clear_after", False)
    st.session_state.summary_offer = None

    if generate_summary:
        with st.spinner("Putting together your session summary..."):
            try:
                summary = commit_session_summary(
                    username,
                    real_messages(chat_history),
                    duration_minutes=current_duration_minutes(),
                )
                if summary:
                    append_message(
                        "assistant",
                        "Saved this in My Journey.\n\n" + summary.get("summary", ""),
                        mood="calm",
                        processed=True,
                    )
                    st.toast("Session summary saved.", icon="💾")
                else:
                    st.toast("Not enough conversation to summarize yet.", icon="ℹ️")
            except Exception as e:
                st.toast(f"Couldn't save summary: {e}", icon="⚠️")

    if clear_after:
        clear_current_chat()
    st.rerun()


def render_summary_offer_controls():
    offer = st.session_state.get("summary_offer")
    if not offer or offer.get("chat") != st.session_state.current_chat:
        return
    st.markdown(
        """
        <div class="glass-card" style="margin:12px 0;">
            <p style="margin:0 0 10px 0; color:#e2e8f0; font-weight:600;">
                Should I put together a quick summary of what we talked about today?
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes please", use_container_width=True, key="summary_yes"):
            finish_summary_offer(True)
    with c2:
        if st.button("No thanks", use_container_width=True, key="summary_no"):
            finish_summary_offer(False)


def render_message_voice_controls(message, idx, settings, user_data, auto_speak=False):
    if message.get("summary_prompt"):
        return
    message.setdefault("id", str(uuid.uuid4()))
    voice_component(
        mode="message_controls",
        messageId=message["id"],
        text=message.get("content", ""),
        lang=get_voice_language(user_data, settings),
        speed=float(settings.get("speaking_speed", 0.85)),
        muted=not settings.get("ai_voice_output", False),
        autoSpeak=auto_speak,
        key=f"voice_controls_{message['id']}_{idx}",
    )


def sync_summaries_to_local_storage(summaries):
    voice_component(
        mode="storage_sync",
        summaries=summaries,
        key=f"summary_storage_{len(summaries)}",
    )


# ═══════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════
user = load_user(username)
user_name = user.get("name") or "User"
stats = user.get("stats", {})
settings = user.get("settings", {})
sync_summaries_to_local_storage(user.get("session_summaries", []))

# AI Orb
st.sidebar.markdown(f"""
<div class="orb-container"><div class="ai-orb mood-{latest_mood}"></div></div>
<div style="text-align:center; margin-bottom:20px;">
    <p class="jarvis-title" style="font-size:1.1rem; letter-spacing:1.5px;">ABHINOVA CORE</p>
    <p style="color:#64748b; font-size:0.75rem; text-transform:uppercase;">Empathetic Neural Interface</p>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

st.sidebar.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Persona Selection ──
st.sidebar.markdown("#### 🎭 Neural Persona")
current_persona = user.get("persona", "friend")

persona_icons = {
    "friend": "🤗",
    "sage": "🧘",
    "coach": "💪",
    "socrates": "🔬"
}

for p_key, p_val in PERSONAS.items():
    is_active = p_key == current_persona
    icon = persona_icons.get(p_key, "👤")
    btn_label = f"✨ {p_val['name']}" if is_active else f"{icon} {p_val['name']}"
    if st.sidebar.button(btn_label, key=f"p_{p_key}", use_container_width=True, help=p_val['description']):
        update_profile(username, persona=p_key)
        st.toast(f"Persona switched to {p_val['name']}", icon="🎭")
        st.rerun()

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Stats Row (Neural Diagnostics) ──
st.sidebar.markdown("<p style='font-size:0.6rem; color:#475569; letter-spacing:1px; margin-bottom:5px;'>// NEURAL_STATS</p>", unsafe_allow_html=True)
s1, s2 = st.sidebar.columns(2)
with s1:
    st.markdown(f'<div style="text-align:center; border:1px solid rgba(56,189,248,0.1); padding:5px; border-radius:4px; background:rgba(0,0,0,0.2);"><div class="stat-value" style="font-size:1.1rem; color:#38bdf8;">{stats.get("total_messages", 0)}</div><div class="stat-label" style="font-size:0.55rem;">PACKETS</div></div>', unsafe_allow_html=True)
with s2:
    st.markdown(f'<div style="text-align:center; border:1px solid rgba(56,189,248,0.1); padding:5px; border-radius:4px; background:rgba(0,0,0,0.2);"><div class="stat-value" style="font-size:1.1rem; color:#10b981;">{stats.get("streak_days", 0)}</div><div class="stat-label" style="font-size:0.55rem;">STREAK_SYC</div></div>', unsafe_allow_html=True)

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

if "current_view" not in st.session_state:
    st.session_state.current_view = "chat"

def change_view(view_name):
    st.session_state.current_view = view_name
    st.session_state.last_activity_at = datetime.now().isoformat()
    st.rerun()

st.sidebar.markdown("#### 📊 Views")
if st.sidebar.button("💬 Chat", use_container_width=True):
    change_view("chat")
if st.sidebar.button("🎙️ Voice Mode", use_container_width=True):
    change_view("voice")
if st.sidebar.button("📊 Dashboard", use_container_width=True):
    change_view("dashboard")
if st.sidebar.button("🌱 My Journey", use_container_width=True):
    change_view("journey")
if settings.get("journal_enabled", True):
    if st.sidebar.button("📓 Thought Journal", use_container_width=True):
        st.session_state.pop("journal_step", None)
        st.session_state.pop("journal_draft", None)
        change_view("journal")

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Chat Management ──
st.sidebar.markdown("#### 💬 Conversations")

if st.sidebar.button("➕ New Chat", use_container_width=True):
    idx = len(st.session_state.chats) + 1
    new_chat = f"💬 Chat {idx}"
    st.session_state.chats[new_chat] = []
    st.session_state.current_chat = new_chat
    st.session_state.chat_started_at[new_chat] = datetime.now().isoformat()
    st.session_state.summary_offer = None
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
            st.session_state.chat_started_at[st.session_state.current_chat] = datetime.now().isoformat()
        st.session_state.summary_offer = None
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
    if len(real_messages(chat_history)) >= 4:
        open_summary_offer("end_button", clear_after=True)
        st.session_state.current_view = "chat"
    else:
        clear_current_chat()
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
    st.markdown("##### Voice")
    voice_input_on = st.toggle("Voice Input", value=settings.get("voice_input", True))
    voice_output_on = st.toggle("AI Voice Output", value=settings.get("ai_voice_output", False))
    lang_values = ["auto", "en", "hi"]
    lang_labels = {"auto": "Auto", "en": "EN", "hi": "HI"}
    current_lang_setting = settings.get("recognition_language", "auto")
    if current_lang_setting not in lang_values:
        current_lang_setting = "auto"
    recognition_lang = st.radio(
        "Recognition Language",
        options=lang_values,
        format_func=lambda value: lang_labels[value],
        index=lang_values.index(current_lang_setting),
        horizontal=True,
    )
    speaking_speed = st.slider(
        "Speaking Speed",
        min_value=0.5,
        max_value=2.0,
        value=float(settings.get("speaking_speed", 0.85)),
        step=0.05,
        format="%.2fx",
    )
    auto_conversation = st.toggle(
        "Auto conversation mode",
        value=settings.get("auto_conversation_mode", False),
    )

    st.markdown("##### Phase 4")
    journal_on = st.toggle("Thought Journal", value=settings.get("journal_enabled", True))
    music_on = st.toggle("Music Therapy", value=settings.get("music_enabled", True))
    notif_on = st.toggle("Check-in Notifications", value=settings.get("notifications_enabled", True))

    new_settings = {
            **settings,
            "mood_tracker": mood_on,
            "typing_animation": typing_on,
            "ambient_halo": halo_on,
            "privacy_pause": settings.get("privacy_pause", False),
            "voice_input": voice_input_on,
            "ai_voice_output": voice_output_on,
            "recognition_language": recognition_lang,
            "speaking_speed": speaking_speed,
            "auto_conversation_mode": auto_conversation,
            "journal_enabled": journal_on,
            "music_enabled": music_on,
            "notifications_enabled": notif_on,
    }
    if new_settings != settings:
        user["settings"] = new_settings
        save_user(username, user)
        st.rerun()

# ── 💾 Data Export & Per-feature Clear ─────────────
with st.sidebar.expander("💾 Privacy & Data"):
    st.caption("All data is local. Export or clear individual feature data.")
    full_export = json.dumps(export_user_data(username), indent=2, ensure_ascii=False)
    st.download_button(
        "⬇ Export all my data (JSON)",
        full_export,
        file_name=f"abhinova_{username}.json",
        mime="application/json",
        use_container_width=True,
    )
    st.markdown("**Clear data for one feature:**")
    cd1, cd2 = st.columns(2)
    with cd1:
        if st.button("Clear Journal", use_container_width=True, key="clr_journal"):
            clear_feature_data(username, "journal"); st.toast("Journal cleared", icon="🗑️"); st.rerun()
        if st.button("Clear Mood logs", use_container_width=True, key="clr_mood"):
            clear_feature_data(username, "mood"); st.toast("Mood logs cleared", icon="🗑️"); st.rerun()
    with cd2:
        if st.button("Clear Music data", use_container_width=True, key="clr_music"):
            clear_feature_data(username, "music"); st.toast("Music data cleared", icon="🗑️"); st.rerun()
        if st.button("Clear Summaries", use_container_width=True, key="clr_summ"):
            clear_feature_data(username, "summaries"); st.toast("Summaries cleared", icon="🗑️"); st.rerun()

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
    header_voice = st.toggle(
        "Speaker",
        value=settings.get("ai_voice_output", False),
        key=f"speaker_toggle_{settings.get('ai_voice_output', False)}",
    )
    if header_voice != settings.get("ai_voice_output", False):
        settings["ai_voice_output"] = header_voice
        user["settings"] = settings
        save_user(username, user)
        st.rerun()
    st.markdown(f"""
    <div style="text-align:right; padding-top:8px;">
        <span style="color:#64748b; font-size:0.8rem;">{datetime.now().strftime("%B %d, %Y • %I:%M %p")}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


def render_dashboard(username):
    st.markdown('<p class="jarvis-title">📊 Progress Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    stats = get_dashboard_stats(username)
    user_data = load_user(username)
    streak = user_data.get("stats", {}).get("streak_days", 0)
    
    # 1. Header Stats
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Check-in Streak", f"{streak} days")
    with c2: st.metric("Avg Mood", f"{stats['avg_mood']} / 10")
    with c3: st.metric("Good Days", f"{stats['good_days']}")
    with c4: st.metric("Messages", stats['total_sessions'])
    
    logs = stats["logs"]
    if not logs:
        st.info("No mood data yet. Check in daily to see your progress!")
        return
        
    df = pd.DataFrame(logs)
    df['date'] = pd.to_datetime(df['date'])
    
    # 2. Mood Line Chart
    st.markdown("### Mood Over Time")
    fig = px.line(df, x='date', y='morningScore', markers=True, title="Daily Mood")
    fig.add_hline(y=5, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    fig.update_traces(line_shape='spline', line=dict(color='#38bdf8', width=3))
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0')
    st.plotly_chart(fig, use_container_width=True)
    
    # 3. Sleep vs Mood Scatter
    if 'sleepQuality' in df.columns:
        st.markdown("### Sleep vs Mood Correlation")
        fig_scatter = px.scatter(df, x='sleepQuality', y='morningScore', trendline="ols")
        fig_scatter.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0')
        st.plotly_chart(fig_scatter, use_container_width=True)

    # 4. Journal analytics
    j = get_journal_stats(username)
    if j["entries_this_month"] > 0:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown("### Thought Patterns This Month")
        jc1, jc2, jc3 = st.columns(3)
        with jc1: st.metric("Entries this month", j["entries_this_month"])
        with jc2: st.metric("Most common pattern", j["most_common_pattern"] or "—")
        with jc3: st.metric("Avg intensity", f"{j['avg_intensity']} / 10")

        if j["distortion_counts"]:
            dist_df = pd.DataFrame(
                [{"Pattern": k, "Count": v} for k, v in j["distortion_counts"].items()]
            ).sort_values("Count", ascending=True)
            fig_dist = px.bar(
                dist_df, x="Count", y="Pattern", orientation="h",
                title="Cognitive Patterns",
            )
            fig_dist.update_traces(marker_color="#818cf8")
            fig_dist.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font_color='#e2e8f0',
            )
            st.plotly_chart(fig_dist, use_container_width=True)

        if j["intensity_series"]:
            int_df = pd.DataFrame(j["intensity_series"])
            int_df["date"] = pd.to_datetime(int_df["date"])
            fig_int = px.line(
                int_df, x="date", y="intensity", markers=True,
                title="Intensity Over Time (lower is gentler)",
            )
            fig_int.update_traces(line_shape='spline', line=dict(color='#a78bfa', width=3))
            fig_int.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font_color='#e2e8f0',
            )
            st.plotly_chart(fig_int, use_container_width=True)


def render_crisis_card():
    helpline_html = "".join(
        f'<p>📞 <a href="{h["tel"]}">{h["name"]}: {h["num"]}</a></p>'
        for h in HELPLINES
    )
    st.markdown(f"""
    <div class="crisis-card">
      <h3>🆘 Main sun raha hoon - tum safe raho.</h3>
      <p><strong>Helplines (24x7, free, India):</strong></p>
      {helpline_html}
      <p><em>Tum akele nahi ho. Kya tum abhi safe ho?</em></p>
    </div>
    """, unsafe_allow_html=True)


def process_pending_ai_response(render_inline=True):
    if not chat_history:
        return
    last_msg = chat_history[-1]
    if last_msg.get("role") != "user" or last_msg.get("processed"):
        return

    user_input = last_msg["content"]
    latest = "neutral"
    for c in reversed(chat_history[:-1]):
        if c["role"] == "assistant" and c.get("mood"):
            latest = c["mood"]
            break

    in_crisis = crisis_check(user_input)
    if in_crisis and render_inline:
        render_crisis_card()

    update_concerns(username, user_input)
    update_stats(username)

    mood = "neutral"
    score = 5
    full_reply = ""
    full_raw = ""

    def run_agent(placeholder=None):
        nonlocal mood, score, full_reply, full_raw
        for evt in therapist_agent(username, user_input, chat_history, in_crisis=in_crisis):
            if evt["done"]:
                mood = evt["mood"]
                score = evt.get("score", 5)
                full_reply = evt["reply"]
                if placeholder is not None:
                    placeholder.markdown(
                        f'<div class="msg-mood-wrap msg-mood-{mood}">{full_reply}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                full_raw += evt["chunk"]
                if placeholder is not None:
                    _, display, _ = parse_mood(full_raw)
                    placeholder.markdown(
                        f'<div class="msg-mood-wrap msg-mood-{latest}">'
                        f'{display}<span class="streaming-cursor">▊</span></div>',
                        unsafe_allow_html=True,
                    )
                    time.sleep(0.02)

    try:
        import time
        if render_inline:
            with st.chat_message("assistant", avatar="🤖"):
                placeholder = st.empty()
                placeholder.markdown(
                    f'<div class="thinking-dots mood-{latest}">'
                    '<span></span><span></span><span></span></div>',
                    unsafe_allow_html=True,
                )
                time.sleep(1.5)
                run_agent(placeholder)
        else:
            with st.spinner("AbhiNova is listening..."):
                run_agent()
    except Exception as e:
        if render_inline:
            st.warning(f"⚠️ Kuch issue hua: {e}\n\nPlease retry.")
        else:
            st.toast(f"Couldn't generate a response: {e}", icon="⚠️")
        full_reply = "⚠️ Couldn't generate a response. Try again?"
        mood = "neutral"
        score = 5

    last_msg["processed"] = True
    append_message(
        "assistant",
        full_reply or "⚠️ Couldn't generate a response. Try again?",
        mood=mood,
        score=score,
    )
    maybe_offer_message_count_summary()
    st.rerun()


def render_journey(username):
    user_data = load_user(username)
    summaries = [normalize_session_summary(s) for s in user_data.get("session_summaries", [])]
    summaries = sorted(summaries, key=lambda s: (s.get("date", ""), s.get("time", "")), reverse=True)
    st.markdown('<p class="jarvis-title">🌱 My Journey</p>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    numeric_moods = [
        s.get("moodEnd") for s in summaries
        if isinstance(s.get("moodEnd"), int)
    ]
    avg_mood = round(sum(numeric_moods) / len(numeric_moods), 1) if numeric_moods else 0
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Sessions total", len(summaries))
    with c2:
        st.metric("Avg mood", avg_mood)

    search = st.text_input("Search by topic", placeholder="work, confidence, sleep...")
    filter_choice = st.radio(
        "Filter",
        ["all", "good sessions", "hard sessions"],
        horizontal=True,
    )

    def include_summary(item):
        topics = [str(t).lower() for t in item.get("topics", [])]
        if search and search.lower() not in " ".join(topics):
            return False
        end = item.get("moodEnd")
        if filter_choice == "good sessions" and isinstance(end, int) and end < 6:
            return False
        if filter_choice == "hard sessions" and isinstance(end, int) and end >= 6:
            return False
        return True

    filtered = [s for s in summaries if include_summary(s)]
    if not filtered:
        st.info("No session summaries yet.")
        return

    for idx, summary in enumerate(filtered):
        topics = summary.get("topics", [])
        topic_html = " ".join(
            f'<span class="concern-badge">{str(topic).replace("_", " ")}</span>'
            for topic in topics
        )
        mood_start = summary.get("moodStart", "?")
        mood_end = summary.get("moodEnd", "?")
        preview = " ".join(summary.get("summary", "").split()[:28])
        with st.container():
            st.markdown(f"""
            <div class="glass-card" style="margin-bottom:10px;">
              <div style="display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap;">
                <strong>{summary.get("date")} • {summary.get("time")}</strong>
                <span style="color:#94a3b8;">{summary.get("durationMinutes", 0)} min</span>
              </div>
              <p style="margin:8px 0; color:#bae6fd;">Mood arc: {mood_start}/10 → {mood_end}/10 📈</p>
              <div>{topic_html}</div>
              <p style="color:#cbd5e1; margin:10px 0 0 0;">{preview}</p>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("Read full"):
                st.markdown(summary.get("summary", ""))
                if st.button("Delete", key=f"delete_summary_{summary['id']}_{idx}"):
                    delete_session_summary(username, summary["id"])
                    st.rerun()


def render_voice_mode(user_data, settings):
    top1, top2 = st.columns([1, 4])
    with top1:
        if st.button("← Back to chat", use_container_width=True):
            st.session_state.current_view = "chat"
            st.rerun()
    with top2:
        st.markdown('<p class="jarvis-title">🎙️ Voice Mode</p>', unsafe_allow_html=True)

    last_assistant = next(
        (m for m in reversed(chat_history) if m.get("role") == "assistant" and not m.get("summary_prompt")),
        {},
    )
    event = voice_component(
        mode="voice_screen",
        voiceInputEnabled=settings.get("voice_input", True),
        muted=not settings.get("ai_voice_output", False),
        autoConversation=settings.get("auto_conversation_mode", False),
        lang=get_voice_language(user_data, settings),
        speed=float(settings.get("speaking_speed", 0.85)),
        lastAssistantId=last_assistant.get("id", ""),
        lastAssistantText=last_assistant.get("content", ""),
        key=f"voice_screen_{st.session_state.current_chat}",
    )
    event = consume_component_event(event)
    if event:
        if event.get("kind") == "send":
            handle_user_text(event.get("text", ""), source="voice")
        elif event.get("kind") == "mute":
            settings["ai_voice_output"] = not event.get("muted", False)
            user_data["settings"] = settings
            save_user(username, user_data)
            st.rerun()


def render_music_player(user_data, settings, mood_tag=None, autoplay=False, key_suffix="default"):
    """Persistent mini player. mood_tag drives default ambient + Spotify suggestion."""
    if not settings.get("music_enabled", True):
        return
    music = music_for_mood(mood_tag or "neutral")
    requested = st.session_state.get("music_request") or {}
    moodKey = requested.get("moodKey") or next(
        (k for k, v in MOOD_TO_MUSIC.items() if v["ambient"] == music["ambient"]),
        "focus",
    )
    expanded = st.session_state.get("music_expanded", False)
    autoplay = autoplay or bool(requested.get("autoplay"))
    # Consume one-shot request after reading
    if requested:
        st.session_state.pop("music_request", None)
    event = music_component(
        ambient=requested.get("ambient", music["ambient"]),
        spotifyId=music["spotifyId"],
        message=music["message"],
        moodKey=moodKey,
        expanded=expanded,
        autoplay=autoplay,
        key=f"music_player_{key_suffix}",
    )
    event = consume_component_event(event)
    if event and event.get("kind") == "feedback":
        add_music_feedback(
            st.session_state.username,
            event.get("moodKey", moodKey),
            event.get("ambient", music["ambient"]),
            event.get("response", "yes"),
        )
        st.toast("Thanks — feedback saved.", icon="🎵")


# ─────────────────────────────────────────
# THOUGHT JOURNAL VIEW
# ─────────────────────────────────────────
def _journal_init_state():
    st.session_state.setdefault("journal_step", "home")
    st.session_state.setdefault("journal_draft", {})


def _journal_reset():
    st.session_state.journal_step = "home"
    st.session_state.journal_draft = {}


def _journal_card(entry):
    first_line = (entry.get("originalThought") or "").splitlines()[0][:100]
    status = "✓ Processed" if entry.get("reframe") else "Draft"
    badge = entry.get("distortionName", "—")
    st.markdown(f"""
    <div class="glass-card" style="margin-bottom:10px;">
      <div style="display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap;">
        <strong>{entry.get("date","")} • {entry.get("time","")}</strong>
        <span style="color:#6ee7b7; font-size:0.78rem;">{status}</span>
      </div>
      <p style="color:#cbd5e1; margin:8px 0 6px 0;">{first_line}</p>
      <span class="concern-badge">{badge}</span>
      <span class="concern-badge">Intensity {entry.get("intensity", 0)}/10</span>
    </div>
    """, unsafe_allow_html=True)


def render_journal(username):
    _journal_init_state()
    step = st.session_state.journal_step
    draft = st.session_state.journal_draft

    top1, top2 = st.columns([1, 5])
    with top1:
        if st.button("← Back", use_container_width=True, key="journal_back"):
            if step == "home":
                st.session_state.current_view = "chat"
            else:
                _journal_reset()
            st.rerun()
    with top2:
        st.markdown('<p class="jarvis-title">📓 Thought Journal</p>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if step == "home":
        if st.button("✏️ New Entry", type="primary", use_container_width=True, key="journal_new"):
            st.session_state.journal_step = "write"
            st.session_state.journal_draft = {}
            st.rerun()

        entries = list(reversed(get_journal_entries(username)))
        tab = st.radio("Filter", ["All", "Processed", "Raw"], horizontal=True, key="journal_filter")
        if tab == "Processed":
            entries = [e for e in entries if e.get("reframe")]
        elif tab == "Raw":
            entries = [e for e in entries if not e.get("reframe")]

        if not entries:
            st.info("No entries yet. Start with a thought that's been on your mind.")
            return
        for entry in entries:
            _journal_card(entry)
            with st.expander("Read full"):
                st.markdown(f"**Original thought:**\n\n> {entry.get('originalThought','')}")
                st.markdown(f"**Intensity:** {entry.get('intensity', 0)}/10")
                if entry.get("q1"):
                    st.markdown(f"**Q1.** {entry['q1']}\n\n→ {entry.get('a1','')}")
                if entry.get("q2"):
                    st.markdown(f"**Q2.** {entry['q2']}\n\n→ {entry.get('a2','')}")
                if entry.get("distortionName"):
                    st.markdown(f"**Pattern:** {entry['distortionName']}")
                    if entry.get("explanation"):
                        st.caption(entry["explanation"])
                    if entry.get("inTheirWords"):
                        st.caption(f"_In your words:_ {entry['inTheirWords']}")
                if entry.get("reframe"):
                    st.markdown(f"**Reframe:**\n\n> {entry['reframe']}")
                    if entry.get("note"):
                        st.caption(entry["note"])
                if st.button("🗑 Delete", key=f"jdel_{entry['id']}"):
                    delete_journal_entry(username, entry["id"])
                    st.rerun()
        return

    if step == "write":
        st.markdown(
            "**What thought or feeling keeps coming back?**  \n"
            "_Write it exactly as it feels — no filters needed._"
        )
        thought = st.text_area(
            "", value=draft.get("originalThought", ""), height=140, key="j_thought",
            label_visibility="collapsed",
        )
        intensity = st.slider("Intensity", 1, 10, value=int(draft.get("intensity", 5)), key="j_intensity")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Cancel", use_container_width=True, key="j_cancel"):
                _journal_reset(); st.rerun()
        with c2:
            if st.button("Next →", type="primary", use_container_width=True, key="j_next1",
                         disabled=not thought.strip()):
                draft["originalThought"] = thought.strip()
                draft["intensity"] = intensity
                with st.spinner("Thinking with you..."):
                    qs = journal_generate_questions(thought.strip(), intensity)
                draft["q1"] = qs["q1"]
                draft["q2"] = qs["q2"]
                st.session_state.journal_draft = draft
                st.session_state.journal_step = "questions"
                st.rerun()
        return

    if step == "questions":
        st.markdown(f"> _{draft.get('originalThought','')}_")
        st.markdown(f"**Q1.** {draft.get('q1','')}")
        a1 = st.text_input("Your answer", value=draft.get("a1", ""), key="j_a1")
        st.markdown(f"**Q2.** {draft.get('q2','')}")
        a2 = st.text_input("Your answer", value=draft.get("a2", ""), key="j_a2")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save as draft", use_container_width=True, key="j_draft"):
                draft["a1"], draft["a2"] = a1.strip(), a2.strip()
                add_journal_entry(username, draft)
                st.toast("Saved as draft.", icon="💾"); _journal_reset(); st.rerun()
        with c2:
            if st.button("Next →", type="primary", use_container_width=True, key="j_next2",
                         disabled=not (a1.strip() and a2.strip())):
                draft["a1"], draft["a2"] = a1.strip(), a2.strip()
                with st.spinner("Looking for a pattern..."):
                    pat = journal_identify_distortion(
                        draft["originalThought"], [draft["a1"], draft["a2"]]
                    )
                draft.update({
                    "distortion": pat["distortion"],
                    "distortionName": pat["name"],
                    "explanation": pat["explanation"],
                    "inTheirWords": pat["in_their_words"],
                })
                st.session_state.journal_draft = draft
                st.session_state.journal_step = "pattern"
                st.rerun()
        return

    if step == "pattern":
        st.markdown(f"### {draft.get('distortionName', 'Balanced Thinking')}")
        if draft.get("distortion") == "balanced":
            st.info(
                "This looks like a balanced thought. Sometimes our minds are just "
                "processing something genuinely difficult."
            )
        else:
            if draft.get("explanation"):
                st.markdown(f"💡 _{draft['explanation']}_")
            if draft.get("inTheirWords"):
                st.markdown(f"**How it shows in your thought:** {draft['inTheirWords']}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Back", use_container_width=True, key="j_back3"):
                st.session_state.journal_step = "questions"; st.rerun()
        with c2:
            if st.button("I understand →", type="primary", use_container_width=True, key="j_next3"):
                with st.spinner("Holding space, writing a gentler version..."):
                    rf = journal_generate_reframe(
                        draft["originalThought"],
                        [draft.get("a1", ""), draft.get("a2", "")],
                        draft.get("distortion", "balanced"),
                    )
                draft["reframe"] = rf["reframe"]
                draft["note"] = rf["note"]
                st.session_state.journal_draft = draft
                st.session_state.journal_step = "reframe"
                st.rerun()
        return

    if step == "reframe":
        st.markdown("#### Before")
        st.markdown(f"> {draft.get('originalThought','')}")
        st.markdown("#### After")
        st.markdown(f"> {draft.get('reframe','')}")
        if draft.get("note"):
            st.caption(draft["note"])
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Try Again", use_container_width=True, key="j_again"):
                with st.spinner("Rewriting..."):
                    rf = journal_generate_reframe(
                        draft["originalThought"],
                        [draft.get("a1", ""), draft.get("a2", "")],
                        draft.get("distortion", "balanced"),
                    )
                draft["reframe"] = rf["reframe"]; draft["note"] = rf["note"]
                st.session_state.journal_draft = draft; st.rerun()
        with c2:
            if st.button("💾 Save Entry", type="primary", use_container_width=True, key="j_save"):
                add_journal_entry(username, draft)
                st.toast("Entry saved.", icon="✅"); _journal_reset(); st.rerun()
        return


# ── Reactive Distress Check ──
is_distressed = crisis_check(chat_history[-1]["content"]) if chat_history and chat_history[-1]["role"] == "user" else False
sad_streak = consecutive_sad_messages(chat_history, window=4) >= 2
if is_distressed or sad_streak:
    st.markdown('<script>document.body.classList.add("distress-mode")</script>', unsafe_allow_html=True)
    st.markdown(f'<div class="ambient-halo mood-calm" style="opacity:0.3;"></div>', unsafe_allow_html=True)

current_view = st.session_state.get("current_view", "chat")

if current_view != "chat":
    # Render Sliding Holographic Panel
    st.markdown('<div class="hologram-panel">', unsafe_allow_html=True)
    
    if current_view == "dashboard":
        render_dashboard(username)
    elif current_view == "journey":
        render_journey(username)
    elif current_view == "journal":
        if not settings.get("journal_enabled", True):
            st.info("JOURNAL_MODULE_OFFLINE")
        else:
            render_journal(username)
            render_music_player(user, settings, mood_tag=latest_mood, key_suffix="journal")
    elif current_view == "voice":
        process_pending_ai_response(render_inline=False)
        render_voice_mode(user, settings)
        render_music_player(user, settings, mood_tag=latest_mood, key_suffix="voice")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

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
assistant_messages = [
    m for m in chat_history
    if m.get("role") == "assistant" and not m.get("summary_prompt")
]
last_assistant_id = assistant_messages[-1].get("id") if assistant_messages else None

for idx, chat in enumerate(chat_history):
    chat.setdefault("id", str(uuid.uuid4()))
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
        if role == "assistant":
            render_message_voice_controls(
                chat,
                idx,
                settings,
                user,
                auto_speak=(
                    settings.get("ai_voice_output", False)
                    and chat.get("id") == last_assistant_id
                ),
            )

# Summary prompt is rendered below after inactivity checks.


# ─────────────────────────────────────────
# AI Music Suggestion (sad/anxious streak)
# ─────────────────────────────────────────
def render_music_suggestion():
    if not settings.get("music_enabled", True):
        return
    if st.session_state.get("music_suggestion_seen", {}).get(st.session_state.current_chat):
        return
    sad_count = consecutive_sad_messages(chat_history, window=6)
    last_assistant_mood = next(
        (m.get("mood") for m in reversed(chat_history)
         if m.get("role") == "assistant" and m.get("mood")),
        None,
    )
    sugg = None
    if sad_count >= 3:
        sugg = ("Would you like some gentle background music? "
                "Sometimes it helps more than words.", "sad", "Yes, play something")
    elif last_assistant_mood == "anxious":
        sugg = ("Try this — put on ocean sounds for 5 minutes and just breathe.",
                "anxious", "Play Ocean Sounds")
    elif last_assistant_mood == "happy" and len(real_messages(chat_history)) >= 6:
        sugg = ("Great conversation today. Want something uplifting to close out?",
                "happy", "Yes! 🎵")
    if not sugg:
        return
    text, mood_key, yes_label = sugg
    st.markdown(f"""
    <div class="glass-card" style="margin:12px 0; border-color:rgba(56,189,248,0.35);">
      <p style="margin:0; color:#cbd5e1;">🎵 {text}</p>
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button(yes_label, use_container_width=True, key=f"musug_yes_{mood_key}"):
            seen = st.session_state.get("music_suggestion_seen", {})
            seen[st.session_state.current_chat] = True
            st.session_state["music_suggestion_seen"] = seen
            st.session_state["music_request"] = {
                "moodKey": mood_key,
                "ambient": MOOD_TO_MUSIC.get(mood_key, MOOD_TO_MUSIC["focus"])["ambient"],
                "autoplay": True,
            }
            st.session_state["music_expanded"] = True
            st.rerun()
    with c2:
        if st.button("No thanks", use_container_width=True, key=f"musug_no_{mood_key}"):
            seen = st.session_state.get("music_suggestion_seen", {})
            seen[st.session_state.current_chat] = True
            st.session_state["music_suggestion_seen"] = seen
            st.rerun()


render_music_suggestion()

# ═══════════════════════════════════════
# AUTO AI RESPONSE (streaming therapist agent)
# ═══════════════════════════════════════
process_pending_ai_response(render_inline=True)

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
maybe_offer_inactivity_summary()
render_summary_offer_controls()

prefill = st.session_state.get("prefill_input", "")
input_event = voice_component(
    mode="chat_input",
    initialText=prefill,
    inputNonce=st.session_state.input_nonce,
    voiceInputEnabled=settings.get("voice_input", True),
    lang=get_voice_language(user, settings),
    speed=float(settings.get("speaking_speed", 0.85)),
    key=f"voice_chat_input_{st.session_state.current_chat}",
)
input_event = consume_component_event(input_event)
if input_event and input_event.get("kind") == "send":
    st.session_state.pop("prefill_input", None)
    handle_user_text(input_event.get("text", ""), source=input_event.get("source", "typed"))

render_music_player(user, settings, mood_tag=latest_mood, key_suffix="chat")
