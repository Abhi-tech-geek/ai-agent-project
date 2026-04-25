import os
import json
from datetime import datetime, date
from openai import OpenAI
from dotenv import load_dotenv
from tools import tool_handler

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "llama-3.3-70b-versatile"
PROFILE_PATH = "user_profile.json"

# ═══════════════════════════════════════════
# USER PROFILE MANAGEMENT
# ═══════════════════════════════════════════

def load_user():
    """Load user profile from JSON file."""
    try:
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "name": "", "role": "", "goal": "",
            "skills": [], "interests": [], "history": [],
            "todos": [],
            "stats": {"total_messages": 0, "tools_used": 0, "streak_days": 0, "last_active": ""}
        }


def save_user(data):
    """Save user profile to JSON file."""
    with open(PROFILE_PATH, "w") as f:
        json.dump(data, f, indent=4)


def update_profile(name=None, role=None, goal=None):
    """Update user profile fields from the UI."""
    user = load_user()
    if name:
        user["name"] = name
    if role:
        user["role"] = role
    if goal:
        user["goal"] = goal
    save_user(user)
    return user


def update_stats():
    """Track usage stats: message count, streak days."""
    user = load_user()
    stats = user.get("stats", {"total_messages": 0, "tools_used": 0, "streak_days": 0, "last_active": ""})

    stats["total_messages"] = stats.get("total_messages", 0) + 1

    today = date.today().isoformat()
    last = stats.get("last_active", "")

    if last == today:
        pass  # Same day, no streak change
    elif last:
        try:
            last_date = date.fromisoformat(last)
            diff = (date.today() - last_date).days
            if diff == 1:
                stats["streak_days"] = stats.get("streak_days", 0) + 1
            elif diff > 1:
                stats["streak_days"] = 1
        except Exception:
            stats["streak_days"] = 1
    else:
        stats["streak_days"] = 1

    stats["last_active"] = today
    user["stats"] = stats
    save_user(user)


def increment_tool_stat():
    """Increment tools used counter."""
    user = load_user()
    stats = user.get("stats", {"total_messages": 0, "tools_used": 0, "streak_days": 0, "last_active": ""})
    stats["tools_used"] = stats.get("tools_used", 0) + 1
    user["stats"] = stats
    save_user(user)


# ═══════════════════════════════════════════
# AUTO LEARNING — SKILL & INTEREST DETECTION
# ═══════════════════════════════════════════

SKILL_KEYWORDS = [
    "python", "java", "javascript", "react", "testing", "automation",
    "selenium", "ai", "ml", "machine learning", "deep learning",
    "sql", "api", "devops", "docker", "kubernetes", "git",
    "html", "css", "node", "flask", "django", "fastapi",
    "aws", "azure", "gcp", "cloud", "linux", "agile", "scrum"
]

INTEREST_KEYWORDS = {
    "ai": "AI/ML",
    "machine learning": "AI/ML",
    "testing": "Testing",
    "automation": "Automation",
    "web": "Web Development",
    "mobile": "Mobile Development",
    "cloud": "Cloud Computing",
    "devops": "DevOps",
    "data": "Data Science",
    "security": "Cybersecurity",
    "blockchain": "Blockchain",
    "game": "Game Development"
}


def detect_skills(text):
    """Detect and update skills from user's message."""
    user = load_user()
    skills = user.get("skills", [])

    for keyword in SKILL_KEYWORDS:
        if keyword in text.lower() and keyword not in skills:
            skills.append(keyword)

    user["skills"] = list(set(skills))
    save_user(user)


def detect_interest(text):
    """Detect and update interests from user's message."""
    user = load_user()
    interests = user.get("interests", [])

    for keyword, interest in INTEREST_KEYWORDS.items():
        if keyword in text.lower() and interest not in interests:
            interests.append(interest)

    user["interests"] = list(set(interests))
    save_user(user)


def track_behavior(text):
    """Track recent user queries for context."""
    user = load_user()
    hist = user.get("history", [])
    hist.append(text)
    user["history"] = hist[-20:]  # Keep last 20
    save_user(user)


# ═══════════════════════════════════════════
# AI-POWERED RECOMMENDATIONS
# ═══════════════════════════════════════════

def recommendations():
    """Generate smart recommendations based on user profile."""
    user = load_user()

    skills = user.get("skills", [])
    interests = user.get("interests", [])
    goal = user.get("goal", "")
    history = user.get("history", [])

    recs = []

    # Skill-based recommendations
    if "python" in skills and "ai" not in skills:
        recs.append("🧠 Learn AI/ML with Python")
    if "testing" in skills and "automation" not in skills:
        recs.append("🤖 Master Test Automation")
    if "python" in skills and "ai" in skills:
        recs.append("🚀 Build AI Projects Portfolio")
    if "javascript" in skills or "react" in skills:
        recs.append("⚡ Explore Full-Stack Development")

    # Interest-based
    if "AI/ML" in interests:
        recs.append("📚 Deep Learning Specialization")
    if "Cloud Computing" in interests:
        recs.append("☁️ Get AWS/Azure Certified")
    if "DevOps" in interests:
        recs.append("🐳 Master Docker & Kubernetes")

    # Goal-based
    if "ai" in goal.lower() or "ml" in goal.lower():
        recs.append("🎯 Start with Kaggle Competitions")
    if "full stack" in goal.lower() or "fullstack" in goal.lower():
        recs.append("🌐 Build a MERN/PERN Stack Project")

    # Default recommendations
    if not recs:
        recs = [
            "📘 Explore a new programming language",
            "🛠️ Build a portfolio project",
            "🎯 Set a 30-day learning goal"
        ]

    return recs[:5]  # Max 5 recommendations


# ═══════════════════════════════════════════
# RESEARCH AGENT
# ═══════════════════════════════════════════

def research_agent(q, history_msgs=None):
    """Research agent: gathers deep information on the topic."""
    if history_msgs is None:
        history_msgs = []

    messages = [
        {"role": "system", "content": "You are a research specialist. Provide factual, detailed, well-structured information. Use markdown formatting."}
    ] + history_msgs + [
        {"role": "user", "content": f"Research this thoroughly: {q}"}
    ]

    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1500
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Research unavailable: {str(e)}"


# ═══════════════════════════════════════════
# TASK PLANNER AGENT
# ═══════════════════════════════════════════

def task_agent(goal):
    """Create a step-by-step actionable plan for any goal."""
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are a strategic task planner. Break down any goal into:
                    1. Clear, numbered steps
                    2. Time estimates for each step
                    3. Resources needed
                    4. Milestones to track progress
                    Use markdown formatting with checkboxes."""
                },
                {"role": "user", "content": goal}
            ],
            max_tokens=1500
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Planning unavailable: {str(e)}"


# ═══════════════════════════════════════════
# DECISION AGENT (FINAL RESPONSE)
# ═══════════════════════════════════════════

def decision_agent(q, research, tool_result, history_msgs=None):
    """Final decision agent: combines all data into a polished response."""
    user = load_user()
    user_name = user.get("name", "User")

    system_prompt = f"""You are AbhiNova AI — a premium personal AI assistant, like Jarvis.

Your personality:
- Professional yet friendly
- Concise but thorough
- Uses clean markdown formatting
- Addresses the user as {user_name}
- Shows expertise and confidence
- Provides actionable insights

User Profile:
- Name: {user.get('name', 'User')}
- Role: {user.get('role', 'Not set')}
- Goal: {user.get('goal', 'Not set')}
- Skills: {', '.join(user.get('skills', []))}
- Interests: {', '.join(user.get('interests', []))}

Rules:
1. Give direct, helpful answers
2. Use markdown headers, bullet points, and code blocks where appropriate
3. If tool data is provided, integrate it naturally into your response
4. Keep responses focused and well-structured
5. End with a subtle suggestion or follow-up question when appropriate"""

    content = f"Query: {q}\n"
    if research:
        content += f"\nResearch Data:\n{research}\n"
    if tool_result:
        content += f"\nTool Result:\n{tool_result}\n"
    content += "\nProvide a comprehensive, well-formatted response."

    if history_msgs is None:
        history_msgs = []

    messages = [
        {"role": "system", "content": system_prompt}
    ] + history_msgs + [
        {"role": "user", "content": content}
    ]

    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=2048
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"⚠️ I encountered an issue: {str(e)}. Please try again."


# ═══════════════════════════════════════════
# 🔥 MAIN ORCHESTRATOR
# ═══════════════════════════════════════════

def multi_agent_with_tools(user_input, chat_history=None):
    """Main orchestrator: routes queries through the multi-agent system.
    
    Returns: (final_response, task_plan, research_data)
    """
    if chat_history is None:
        chat_history = []

    # Build history context (last 10 messages)
    history_msgs = []
    for msg in chat_history[-10:]:
        content = msg.get("content", "")
        role = msg.get("role", "user")
        # Skip overly long messages
        if len(content) > 1500:
            content = content[:1500] + "..."
        # Skip processed flags
        if role in ["user", "assistant"]:
            history_msgs.append({"role": role, "content": content})

    # Auto-learn from user input
    detect_skills(user_input)
    detect_interest(user_input)
    track_behavior(user_input)
    update_stats()

    # ─── STEP 1: Try direct tool match ───
    tool_output = tool_handler(user_input)

    if tool_output:
        increment_tool_stat()
        tool_name = tool_output.get("tool", "tool")
        tool_result = tool_output.get("output", "")

        # Simple tools → return directly (saves API calls)
        if tool_name in ["calculator", "weather", "generate_image", "todo_manager", "motivation"]:
            return tool_result, None, None

        # Complex tools → pass through decision agent for polished output
        final = decision_agent(user_input, None, tool_result, history_msgs)
        return final, None, None

    # ─── STEP 2: Task planning mode ───
    task = None
    task_triggers = ["learn", "roadmap", "plan", "steps to", "how to become", "guide me", "path to"]
    if any(trigger in user_input.lower() for trigger in task_triggers):
        task = task_agent(user_input)

    # ─── STEP 3: Research + Decision ───
    research = research_agent(user_input, history_msgs)
    final = decision_agent(user_input, research, None, history_msgs)

    return final, task, research