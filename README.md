# 🤖 AbhiNova AI — Personal Intelligence System

> A premium Jarvis-like AI personal assistant powered by multi-agent architecture and Groq LLM.

---

## ✨ Features

### 🧠 Multi-Agent System
- **Research Agent** — Deep information gathering
- **Decision Agent** — Polished final response generation
- **Task Planner** — Step-by-step actionable plans
- **Tool Router** — Intelligent tool selection & execution

### 🔧 AI-Powered Tools (12+)
| Tool | Description |
|------|-------------|
| 🧮 Calculator | Safe math expression evaluation |
| 🌤️ Weather | Live weather with detailed metrics |
| 📧 Email Writer | AI-crafted professional emails |
| 💻 Code Generator | Production-ready code generation |
| 🧪 Test Cases | Comprehensive QA test case generation |
| 🤔 Decision Maker | Pros/cons analysis with recommendations |
| 🌐 Web Search | DuckDuckGo-powered internet search |
| 📄 URL Reader | Read and extract content from any URL |
| 🎨 Image Creator | AI image generation via Pollinations |
| 📝 Summarizer | Intelligent text/article summarization |
| 🌍 Translator | Multi-language translation |
| 📋 Todo Manager | Personal task tracking system |
| 😂 Motivation | Jokes and motivational quotes |

### 🎯 Smart Features
- **Auto-learning** — Detects your skills & interests from conversations
- **Smart Recommendations** — Personalized learning/career suggestions
- **Usage Stats** — Track messages, tools used, and streak days
- **Chat Export** — Download conversations as markdown
- **Profile System** — Editable user profile with skill badges

### 🎨 Premium UI/UX
- Jarvis-inspired dark theme with glassmorphism
- Animated AI orb with pulse effect
- Time-based greeting system
- Quick action cards grid
- Smooth message animations
- Responsive sidebar with stats dashboard

---

## 🛠️ Tech Stack

- **Python** + **Streamlit**
- **Groq API** (LLaMA 3.3 70B)
- **DuckDuckGo Search**
- **Pollinations AI** (Image Generation)

---

## 📁 Project Structure
```
ai-agent-project/
├── app.py              # Streamlit UI (Jarvis theme)
├── multi_agent.py      # Multi-agent orchestrator
├── tools.py            # AI-powered tool implementations
├── user_profile.json   # User data & preferences
├── logo.png            # AbhiNova AI logo
├── requirements.txt    # Dependencies
└── .env                # API keys (gitignored)
```

---

## ⚙️ Setup

```bash
# Clone the repository
git clone https://github.com/your-username/ai-agent-project.git
cd ai-agent-project

# Install dependencies
pip install -r requirements.txt

# Add your API keys to .env
echo "GROQ_API_KEY=your_key_here" > .env

# Run the app
streamlit run app.py
```

---

## 🚀 How It Works
1. User enters a query
2. Tool Router checks if a specialized tool is needed
3. If tool found → executes and returns formatted result
4. If not → Research Agent gathers information
5. Decision Agent combines everything into a polished response
6. Skills, interests, and stats are tracked automatically

---

Built with ❤️ by **Abhinav**
