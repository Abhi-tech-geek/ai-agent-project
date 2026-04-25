import streamlit as st
import time
from datetime import datetime
from multi_agent import (
    multi_agent_with_tools, load_user, save_user,
    recommendations, update_profile
)

# ═══════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════
st.set_page_config(
    page_title="AbhiNova AI — Personal Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════
if "chats" not in st.session_state:
    st.session_state.chats = {"💬 Chat 1": []}
    st.session_state.current_chat = "💬 Chat 1"
if "show_profile_setup" not in st.session_state:
    st.session_state.show_profile_setup = False

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
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #38bdf8, #0284c7, #0369a1, #1e3a5f);
    box-shadow: 0 0 30px rgba(56, 189, 248, 0.4), 0 0 60px rgba(56, 189, 248, 0.15), inset 0 0 20px rgba(56, 189, 248, 0.3);
    animation: orbPulse 3s ease-in-out infinite;
}

@keyframes orbPulse {
    0%, 100% { box-shadow: 0 0 30px rgba(56,189,248,0.4), 0 0 60px rgba(56,189,248,0.15); transform: scale(1); }
    50% { box-shadow: 0 0 45px rgba(56,189,248,0.6), 0 0 80px rgba(56,189,248,0.25); transform: scale(1.05); }
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
user = load_user()
user_name = user.get("name") or "User"
stats = user.get("stats", {})

# AI Orb
st.sidebar.markdown("""
<div class="orb-container"><div class="ai-orb"></div></div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div style="text-align:center; margin-bottom:8px;">
    <p class="jarvis-title" style="font-size:1.2rem;">ABHINOVA AI</p>
    <p class="jarvis-sub">Personal Intelligence System</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Stats Row ──
s1, s2, s3 = st.sidebar.columns(3)
with s1:
    st.markdown(f'<div style="text-align:center"><div class="stat-value">{stats.get("total_messages", 0)}</div><div class="stat-label">Messages</div></div>', unsafe_allow_html=True)
with s2:
    st.markdown(f'<div style="text-align:center"><div class="stat-value">{stats.get("tools_used", 0)}</div><div class="stat-label">Tools</div></div>', unsafe_allow_html=True)
with s3:
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

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Profile Section ──
st.sidebar.markdown("#### 👤 Profile")

if user.get("name"):
    st.sidebar.markdown(f"**{user['name']}**")
if user.get("role"):
    st.sidebar.markdown(f"*{user['role']}*")
if user.get("goal"):
    st.sidebar.markdown(f"🎯 {user['goal']}")

# Skills as badges
skills = user.get("skills", [])
if skills:
    badges = " ".join([f'<span class="skill-badge">{s}</span>' for s in skills[:8]])
    st.sidebar.markdown(f"<div style='margin:8px 0'>{badges}</div>", unsafe_allow_html=True)

# Profile edit
with st.sidebar.expander("✏️ Edit Profile"):
    new_name = st.text_input("Name", value=user.get("name", ""), key="pname")
    new_role = st.text_input("Role", value=user.get("role", ""), key="prole")
    new_goal = st.text_input("Goal", value=user.get("goal", ""), key="pgoal")
    if st.button("💾 Save Profile", use_container_width=True):
        update_profile(new_name, new_role, new_goal)
        st.rerun()

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Recommendations ──
st.sidebar.markdown("#### 🚀 Recommendations")
try:
    recs = recommendations()
    for r in recs:
        st.sidebar.markdown(f'<div class="rec-item">{r}</div>', unsafe_allow_html=True)
except Exception:
    st.sidebar.info("No recommendations yet")

st.sidebar.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Status ──
st.sidebar.markdown(f"""
<div class="sidebar-status">
    ⚡ AbhiNova AI — Online
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
# CHAT DATA
# ═══════════════════════════════════════
chat_history = st.session_state.chats[st.session_state.current_chat]


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
        <p class="greeting-sub">How can I assist you today?</p>
    </div>
    """, unsafe_allow_html=True)

    # Quick Actions — compact cards (clickable directly)
    st.markdown("""<div class="home-animated home-delay-2">
        <p style='text-align:center; color:#475569; font-size:0.75rem; letter-spacing:2px; text-transform:uppercase; margin:16px 0 8px 0;'>⚡ Quick Actions</p>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🌤️  Weather", key="qa_weather", use_container_width=True):
            chat_history.append({"role": "user", "content": "What's the weather in Delhi?"})
            st.rerun()
    with c2:
        if st.button("🧮  Calculator", key="qa_calc", use_container_width=True):
            chat_history.append({"role": "user", "content": "Calculate 245 * 18 + 320"})
            st.rerun()
    with c3:
        if st.button("🌐  Web Search", key="qa_search", use_container_width=True):
            chat_history.append({"role": "user", "content": "Search latest AI news 2026"})
            st.rerun()

    c4, c5, c6 = st.columns(3)
    with c4:
        if st.button("📧  Email Writer", key="qa_email", use_container_width=True):
            chat_history.append({"role": "user", "content": "Write email to manager about project update"})
            st.rerun()
    with c5:
        if st.button("💻  Code Gen", key="qa_code", use_container_width=True):
            chat_history.append({"role": "user", "content": "Write code for a Python REST API with Flask"})
            st.rerun()
    with c6:
        if st.button("🎨  Image AI", key="qa_image", use_container_width=True):
            chat_history.append({"role": "user", "content": "Generate image of a futuristic AI city"})
            st.rerun()

    # Suggestion chips
    st.markdown("""<div class="home-animated home-delay-3">
        <p style='text-align:center; color:#475569; font-size:0.75rem; letter-spacing:2px; text-transform:uppercase; margin:20px 0 8px 0;'>💡 Try Asking</p>
    </div>""", unsafe_allow_html=True)

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        if st.button("📘 Python Roadmap", use_container_width=True):
            chat_history.append({"role": "user", "content": "Give me a complete Python learning roadmap"})
            st.rerun()
    with s2:
        if st.button("🧠 Explain AI", use_container_width=True):
            chat_history.append({"role": "user", "content": "What is AI and how does it work?"})
            st.rerun()
    with s3:
        if st.button("💼 Career Guide", use_container_width=True):
            chat_history.append({"role": "user", "content": "Career guidance for becoming an AI engineer"})
            st.rerun()
    with s4:
        if st.button("📝 My Todos", use_container_width=True):
            chat_history.append({"role": "user", "content": "Show my todos"})
            st.rerun()


# ═══════════════════════════════════════
# DISPLAY CHAT MESSAGES
# ═══════════════════════════════════════
for chat in chat_history:
    avatar = "🤖" if chat["role"] == "assistant" else "👤"
    with st.chat_message(chat["role"], avatar=avatar):
        st.markdown(chat["content"])


# ═══════════════════════════════════════
# AUTO AI RESPONSE (for pending messages)
# ═══════════════════════════════════════
if chat_history:
    last_msg = chat_history[-1]

    if last_msg["role"] == "user" and "processed" not in last_msg:
        user_input = last_msg["content"]
        last_msg["processed"] = True

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("⚡ AbhiNova is thinking..."):
                try:
                    final, task, research = multi_agent_with_tools(user_input, chat_history)
                except Exception as e:
                    final = f"⚠️ Something went wrong: {str(e)}\n\nPlease check your API key in the `.env` file."
                    task, research = None, None

            # Show thought process
            if task or research:
                with st.expander("🧠 Thought Process"):
                    if task:
                        st.markdown(f"**📋 Task Plan:**\n{task}")
                    if research:
                        st.markdown(f"**🔍 Research:**\n{research}")

            # Typing animation
            if final:
                placeholder = st.empty()
                typed = ""
                for char in str(final):
                    typed += char
                    placeholder.markdown(typed)
                    time.sleep(0.003)

        chat_history.append({
            "role": "assistant",
            "content": str(final) if final else "I couldn't generate a response. Please try again."
        })
        st.rerun()


# ═══════════════════════════════════════
# CHAT INPUT
# ═══════════════════════════════════════
user_input = st.chat_input("Ask AbhiNova anything...")

if user_input:
    chat_history.append({
        "role": "user",
        "content": user_input
    })
    st.rerun()