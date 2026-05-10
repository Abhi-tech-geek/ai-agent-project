# 🤖 AbhiNova AI — Empathetic AI Therapist

> A premium, Jarvis-inspired AI Personal Therapist designed for emotional well-being. Built with high-performance LLaMA 3.3 70B (via Groq) and a futurist glassmorphism UI.

---

## ✨ Features

### 🧠 Empathetic AI Core
*   **Persona Engine** — Switch between specialized therapist modes: *The Friend, The Sage, The Coach, and The Logical One*.
*   **Intelligent Auto-Learning** — Organically identifies underlying life concerns (Work, Anxiety, Relationships, Sleep) from context.
*   **CBT Thought Journal** — A 4-step guided Cognitive Behavioral Therapy framework to identify and reframe cognitive distortions.
*   **Session Synthesis** — Automatic summarization of long chats with theme extraction and "Mood Arc" tracking.
*   **Safety First** — Deterministic real-time crisis detection with immediate access to 24/7 helplines.

### 🎯 Proactive Features
*   **Daily Mood Matrix** — Log mood scores, emotional tags, and sleep quality to track trends.
*   **Music & Sound Therapy** — Dynamic ambient soundscapes and Spotify suggestions tailored to your real-time emotional state.
*   **Futurist Voice Mode** — Full duplex voice interaction with custom speaking speeds and multi-language recognition (Hindi/English).
*   **Progress Analytics** — Rich Plotly-powered dashboards visualizing correlations between sleep, mood, and journaling patterns.

### 🎨 Premium UI/UX (Jarvis Aesthetic)
*   **Dynamic AI Orb** — A pulsing, color-shifting orb that reacts to the AI's "mood" and thinking state.
*   **Glassmorphism Theme** — Deep blue frosted glass UI with smooth micro-animations and glowing transitions.
*   **Ambient Halo** — A subtle screen-wide glow that changes color based on the conversation's emotional tone.

---

## 🛠️ Technical Architecture

### 🛡️ Security & Reliability
*   **Salted Hashing** — Passwords secured using `PBKDF2-HMAC-SHA256` with unique 16-byte salts and 100,000 iterations.
*   **Concurrency Engine** — Robust file-level locking via `filelock` to prevent data corruption during multi-user sessions.
*   **Local-First Privacy** — All chat history, journals, and personal profiles are stored locally in the `profiles/` directory.

### 📦 Tech Stack
*   **Backend:** Python 3.14+, Streamlit
*   **LLM Intelligence:** Groq (LLaMA 3.3 70B)
*   **Visualization:** Plotly & Pandas
*   **Database:** Local JSON with Atomic File Locking

---

## 📁 Project Structure
```text
ai-agent-project/
├── app.py              # Main Streamlit Application (UI & Orchestration)
├── therapist.py        # Core Business Logic, CBT Engine, & Prompt Engineering
├── components/         # Custom React components (Voice & Music Player)
├── profiles/           # Encrypted-at-rest (Hashed) local user profiles
├── tests/              # Comprehensive Pytest suite (85+ cases)
├── users.json          # Authenticated User Registry
└── requirements.txt    # Project Dependencies
```

---

## ⚙️ Quick Start

```bash
# 1. Clone & Navigate
git clone https://github.com/your-username/ai-agent-project.git
cd ai-agent-project

# 2. Environment Setup
pip install -r requirements.txt

# 3. Configure API Keys
echo "GROQ_API_KEY=your_key_here" > .env

# 4. Launch Experience
streamlit run app.py
```

---

Built with ❤️ by **Abhinav**
