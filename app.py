import streamlit as st
import time
from multi_agent import multi_agent_with_tools, load_user, recommendations

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="AbhiNova AI", page_icon="🤖", layout="wide")

# -----------------------
# SESSION STATE
# -----------------------
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
    st.session_state.current_chat = "Chat 1"

# -----------------------
# CSS
# -----------------------
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at 20% 20%, #0f172a, #020617);
    color: white;
}

h1, h2 {
    color: #38bdf8;
}

div.stButton > button {
    border-radius: 12px;
    border: 1px solid #38bdf8;
    background-color: transparent;
    color: white;
    padding: 10px 20px;
}

div.stButton > button:hover {
    background-color: #38bdf8;
    color: black;
}

section[data-testid="stSidebar"] {
    background-color: #020617;
}

.glow {
    color: #38bdf8;
    text-shadow: 0 0 10px #38bdf8;
}
</style>
""", unsafe_allow_html=True)

# -----------------------
# SIDEBAR
# -----------------------

col1, col2, col3 = st.sidebar.columns([1,2,1])
with col2:
    st.image("logo.png", width=120)

user = load_user()

user_name = user.get("name") or "Abhinav"

st.sidebar.markdown(f"""
### 🤖 {user_name}'s AI
🚀 *Your Growth Dashboard*
""")

# CHAT SYSTEM
st.sidebar.markdown("### 💬 Chats")

if st.sidebar.button("➕ New Chat"):
    new_chat = f"Chat {len(st.session_state.chats)+1}"
    st.session_state.chats[new_chat] = []
    st.session_state.current_chat = new_chat
    st.rerun()

for chat_name in st.session_state.chats.keys():
    if st.sidebar.button(chat_name):
        st.session_state.current_chat = chat_name
        st.rerun()

if st.sidebar.button("🗑 Delete Current Chat"):
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[st.session_state.current_chat]
        st.session_state.current_chat = list(st.session_state.chats.keys())[0]
    else:
        st.session_state.chats[st.session_state.current_chat] = []
    st.rerun()

st.sidebar.markdown("---")

# PROFILE
st.sidebar.markdown("### 👤 You")
if user.get("name"):
    st.sidebar.markdown(f"👋 **{user['name']}**")

skills = user.get("skills", [])
if skills:
    st.sidebar.markdown("### ⚡ Skills")
    for s in skills:
        st.sidebar.markdown(f"• {s}")

# RECOMMENDATIONS
st.sidebar.markdown("### 🚀 Recommendations")
try:
    recs = recommendations()
    for r in recs:
        st.sidebar.markdown(f"👉 {r}")
except:
    st.sidebar.info("No recommendations")

st.sidebar.markdown("---")
st.sidebar.success("✨ Smart AI Active")

# -----------------------
# HEADER
# -----------------------
st.markdown("<h2 class='glow'>🤖 AbhiNova AI</h2>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8;'>🚀 Your Personal AI Growth Partner</p>", unsafe_allow_html=True)
st.markdown("---")

# -----------------------
# CHAT DATA
# -----------------------
chat_history = st.session_state.chats[st.session_state.current_chat]

# -----------------------
# HOME UI
# -----------------------
if len(chat_history) == 0:

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.markdown("<h1 style='text-align:center;'>Start your AI journey 🚀</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#94a3b8;'>Ask anything. Learn faster. Grow smarter.</p>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;'>💡 Try asking:</h3>", unsafe_allow_html=True)

        b1, b2, b3 = st.columns(3)

        with b1:
            if st.button("📘 Python roadmap"):
                chat_history.append({"role":"user","content":"Python roadmap"})
                st.rerun()

        with b2:
            if st.button("🧠 What is AI"):
                chat_history.append({"role":"user","content":"What is AI"})
                st.rerun()

        with b3:
            if st.button("💼 Career guidance"):
                chat_history.append({"role":"user","content":"Career guidance"})
                st.rerun()

# -----------------------
# DISPLAY CHAT
# -----------------------
for chat in chat_history:
    with st.chat_message(chat["role"]):
        st.markdown(chat["content"])

# -----------------------
# AUTO AI RESPONSE (for suggestion click)
# -----------------------
if chat_history:
    last_msg = chat_history[-1]

    if last_msg["role"] == "user" and "processed" not in last_msg:

        user_input = last_msg["content"]

        # mark processed (duplicate call avoid)
        last_msg["processed"] = True

        with st.chat_message("assistant"):
            with st.spinner("🤖 Thinking..."):
                response = multi_agent_with_tools(user_input)

            # typing animation
            placeholder = st.empty()
            typed = ""
            for char in response:
                typed += char
                placeholder.markdown(typed)
                time.sleep(0.005)

        chat_history.append({
            "role": "assistant",
            "content": response
        })

        st.rerun()



# -----------------------
# INPUT
# -----------------------
user_input = st.chat_input("Ask anything...")

if user_input:
    chat_history.append({
        "role": "user",
        "content": user_input
    })

    st.rerun()