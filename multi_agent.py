import os, json
from openai import OpenAI
from dotenv import load_dotenv
from tools import tool_handler

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)
# AI TOOL SELECTOR
# ------------------------
def ai_tool_selector(query):

    prompt = f"""
    You are an AI tool selector.

    User Query: {query}

    Available tools:
    - calculator → for math
    - weather → for weather info
    - email_writer → for writing emails
    - test_case_generator → for testing
    - code_generator → for coding
    - web_search → for latest info

    Answer ONLY one word:
    tool name OR "none"
    """

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content.strip().lower()

# ------------------------
# USER LOAD / SAVE
# ------------------------
def load_user():
    try:
        with open("user_profile.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_user(data):
    with open("user_profile.json", "w") as f:
        json.dump(data, f, indent=4)

# ------------------------
# SETUP USER
# ------------------------
def setup_user():
    user = load_user()

    user.setdefault("skills", [])
    user.setdefault("interests", [])
    user.setdefault("history", [])

    if not user.get("name"):
        user["name"] = input("Naam kya hai? ")

    if not user.get("role"):
        user["role"] = input("Kya karte ho? ")

    if not user.get("goal"):
        user["goal"] = input("Goal kya hai? ")

    save_user(user)

# ------------------------
# AUTO LEARNING
# ------------------------
def detect_skills(text):
    user = load_user()
    user["skills"] = user.get("skills", [])

    keywords = ["python","testing","automation","ai","java"]

    for k in keywords:
        if k in text.lower():
            user["skills"].append(k)

    user["skills"] = list(set(user["skills"]))
    save_user(user)


def detect_interest(text):
    user = load_user()
    user["interests"] = user.get("interests", [])

    if "ai" in text.lower():
        user["interests"].append("AI")

    if "testing" in text.lower():
        user["interests"].append("Testing")

    user["interests"] = list(set(user["interests"]))
    save_user(user)


def track_behavior(text):
    user = load_user()
    hist = user.get("history", [])
    hist.append(text)
    user["history"] = hist[-10:]
    save_user(user)

# ------------------------
# RECOMMENDATION ENGINE
# ------------------------
def recommendations():
    user = load_user()

    rec = []

    if "testing" in user["skills"]:
        rec.append("Learn Automation Testing")

    if "python" in user["skills"]:
        rec.append("Move to AI/ML")

    if "AI" in user["interests"]:
        rec.append("Build ML Projects")

    return rec

# ------------------------

# ------------------------
# RESEARCH
# ------------------------
def research_agent(q):
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":q}]
    )
    return res.choices[0].message.content

# ------------------------
# FINAL DECISION
# ------------------------
def decision_agent(q, research, tool):
    user = load_user()

    content = f"""
User: {user}

Recommendations: {recommendations()}

Query: {q}
Research: {research}
Tool: {tool}
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":content}]
    )
    return res.choices[0].message.content


# ------------------------
# TASK AGENT (AUTO MODE)
# ------------------------
def task_agent(goal):
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a task planning AI. Break user goal into step-by-step actionable plan."
            },
            {
                "role": "user",
                "content": goal
            }
        ]
    )

    return res.choices[0].message.content


# ------------------------
# MAIN
# ------------------------
def multi_agent_with_tools(user_input):

    detect_skills(user_input)
    detect_interest(user_input)
    track_behavior(user_input)

    # 🔥 TOOL CHECK
    tool_output = tool_handler(user_input)

    if not tool_output:
        tool_name = ai_tool_selector(user_input)

        if tool_name != "none":
            tool_output = tool_handler(user_input)

    # 🔥 TASK MODE
    task = None
    if not tool_output and any(x in user_input.lower() for x in ["learn", "roadmap", "plan"]):
        task = task_agent(user_input)

    # 🔥 💥 MAIN FIX START

    # ✅ CASE 1: Tool found → STOP everything
    # TOOL FOUND
    if tool_output:
        tool_name = tool_output.get("tool", "tool")
        tool_result = tool_output.get("output", "")

        # ✅ SIMPLE TOOLS → direct return
        if tool_name in ["calculator", "weather"]:
            return f"🔧 {tool_name.upper()}\n\n{tool_result}"

        # 🔥 SMART TOOLS → AI improve karega
        improved = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional assistant. Improve formatting, grammar, and clarity."},
                {"role": "user", "content": tool_result}
            ]
        ).choices[0].message.content

        return f"✨ {tool_name.upper()} (Enhanced)\n\n{improved}"

    # 🔥 CASE 2: No tool → continue AI flow

    research = research_agent(user_input)
    final = decision_agent(user_input, research, None)

    output = ""

    if task:
        output += f"🧠 Task Plan:\n{task}\n\n"

    if research:
        output += f"🔍 Research:\n{research}\n\n"

    output += f"🤖 Final Answer:\n{final}"

    return output