# 🤖 AbhiNova AI

AbhiNova AI is a smart personal AI assistant built using a multi-agent architecture.  
It helps users learn, solve problems, and automate tasks using a combination of AI and tools.

---

## 🚀 Description

AbhiNova AI is designed to go beyond a basic chatbot.  
It can intelligently decide:

- Whether to answer directly 🤖  
- Or use a tool (calculator, weather, email, etc.) 🔧  
- Or combine both for better results  

It also learns from user behavior to provide smarter recommendations over time.

---

## ✨ Features

### 🧠 Multi-Agent System
- Research Agent → gathers information  
- Decision Agent → generates final answer  
- Tool Handler → executes tools  

---

### 🔧 Smart Tool Integration

Available tools:

- 🧮 Calculator → solves math problems  
- 🌤 Weather → fetches live weather  
- 📧 Email Writer → creates professional emails  
- 💻 Code Generator → generates code  
- 🧪 Test Case Generator → testing scenarios  
- 🌐 Web Search → latest information  

---

### ⚡ Hybrid Intelligence (AI + Tools)

- Tools → fast & accurate  
- AI → smart & well-formatted  

👉 Combined output = better results

---

### 👤 User Learning System

Tracks:
- Skills  
- Interests  
- History  

👉 Enables personalized experience

---

### 🎯 Recommendation Engine

Suggests:
- Learning paths  
- Skills to improve  
- Career direction  

---

### 🖥️ Clean UI

- Chat-based interface  
- Suggestion buttons  
- Tool result formatting  
- Sidebar profile  

---

## 🧰 Tech Stack

- Python  
- Streamlit  
- Groq API (LLM - LLaMA models)  
- DuckDuckGo Search  
- Requests  
- dotenv  

---

## 📁 Project Structure
ai-agent-project/

├── app.py # Streamlit UI
├── multi_agent.py # AI logic (agents + flow)
├── tools.py # Tool implementations
├── user_profile.json # User data
├── requirements.txt # Dependencies
├── .env # API keys (ignored)

## ⚙️ How It Works
User enters a query
System checks if a tool is needed
If needed → tool executes
If not → AI generates response
For complex queries:
Task planning 🧠
Research 🔍
Final structured answer is shown


