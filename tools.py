import os
import re
import ast
import operator
import requests
import urllib.parse
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------
# GROQ CLIENT (shared for AI-powered tools)
# -------------------------------------------
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "llama-3.3-70b-versatile"


def _ai_generate(system_prompt, user_prompt, max_tokens=1024):
    """Helper: call Groq LLM for AI-powered tools."""
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI generation failed: {str(e)}"


# -------------------------------------------
# 🧮 CALCULATOR (safe eval)
# -------------------------------------------
def calculator(expression):
    try:
        expr = re.sub(r'[^0-9+\-*/().]', '', expression)
        if not expr:
            return "❌ Invalid expression"

        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg
        }

        def eval_(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                return ops[type(node.op)](eval_(node.left), eval_(node.right))
            elif isinstance(node, ast.UnaryOp):
                return ops[type(node.op)](eval_(node.operand))
            else:
                raise TypeError(f"Unsupported: {node}")

        result = eval_(ast.parse(expr, mode='eval').body)
        return f"**🧮 Result:** `{expression}` = **{result}**"
    except ZeroDivisionError:
        return "❌ Division by zero!"
    except Exception:
        return "❌ Invalid calculation. Try something like: `calculate 25 * 4`"


# -------------------------------------------
# 🌤️ WEATHER
# -------------------------------------------
def weather(query):
    try:
        match = re.search(r'(?:in|of|for|at)\s+([a-zA-Z\s]+)', query, re.IGNORECASE)
        city = match.group(1).strip() if match else query.split()[-1]
        city = city.strip("?.,!")

        url = f"https://wttr.in/{city}?format=%t+%C+%h+%w"
        response = requests.get(url, timeout=5)
        response.encoding = "utf-8"

        data = response.text.strip()

        # Also get the detailed format
        url2 = f"https://wttr.in/{city}?format=%t|%C|%h|%w|%p"
        r2 = requests.get(url2, timeout=5)
        r2.encoding = "utf-8"
        parts = r2.text.strip().split("|")

        temp = parts[0] if len(parts) > 0 else "N/A"
        condition = parts[1] if len(parts) > 1 else "N/A"
        humidity = parts[2] if len(parts) > 2 else "N/A"
        wind = parts[3] if len(parts) > 3 else "N/A"

        return f"""**🌤️ Weather in {city.title()}**

| Parameter | Value |
|-----------|-------|
| 🌡️ Temperature | {temp} |
| ☁️ Condition | {condition} |
| 💧 Humidity | {humidity} |
| 🌬️ Wind | {wind} |
"""
    except Exception:
        return "⚠️ Weather service unavailable. Please try again."


# -------------------------------------------
# 📧 EMAIL WRITER (AI-Powered)
# -------------------------------------------
def email_writer(prompt):
    system = """You are a professional email writer. Write clear, concise, and professional emails.
    Format the output with Subject line, proper greeting, body, and sign-off.
    Use markdown formatting. Sign off as the user's name."""

    return _ai_generate(system, f"Write a professional email about: {prompt}")


# -------------------------------------------
# 🧪 TEST CASE GENERATOR (AI-Powered)
# -------------------------------------------
def test_case_generator(feature):
    system = """You are a QA testing expert. Generate comprehensive test cases including:
    - Positive test cases
    - Negative test cases  
    - Edge cases
    - Boundary value tests
    Format each test case with: ID, Description, Steps, Expected Result, Priority.
    Use markdown tables for clean formatting."""

    return _ai_generate(system, f"Generate detailed test cases for: {feature}", max_tokens=2048)


# -------------------------------------------
# 💻 CODE GENERATOR (AI-Powered)
# -------------------------------------------
def code_generator(prompt):
    system = """You are an expert programmer. Generate clean, well-commented, production-ready code.
    Include:
    - Proper imports
    - Error handling
    - Docstrings
    - Usage examples
    Use markdown code blocks with proper syntax highlighting."""

    return _ai_generate(system, f"Write code for: {prompt}", max_tokens=2048)


# -------------------------------------------
# 🤔 DECISION MAKER (AI-Powered)
# -------------------------------------------
def decision_maker(problem):
    system = """You are a strategic decision advisor. Analyze the problem and provide:
    - Clear pros and cons
    - Risk assessment
    - Data-driven recommendation
    - Action steps
    Use markdown formatting with tables and headers."""

    return _ai_generate(system, f"Help me decide: {problem}")


# -------------------------------------------
# 🌐 WEB SEARCH
# -------------------------------------------
def web_search(query):
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(f"**{r['title']}**\n{r['body']}\n🔗 {r.get('href', '')}")

        if results:
            return "**🌐 Search Results:**\n\n" + "\n\n---\n\n".join(results)
        return "No results found for this query."
    except Exception as e:
        return f"⚠️ Search failed: {str(e)}"


# -------------------------------------------
# 📄 URL READER
# -------------------------------------------
def read_url(query):
    try:
        match = re.search(r'(https?://[^\s]+)', query)
        if not match:
            return "❌ No URL found in your message. Please include a valid URL."

        url = match.group(1).rstrip(".,;!?)")
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        text = re.sub(r'<[^>]+>', ' ', res.text)
        text = re.sub(r'\s+', ' ', text).strip()

        content = text[:2000]
        return f"**📄 Content from** [{url}]({url}):\n\n{content}..."
    except Exception:
        return "⚠️ Could not read URL. It may be blocked or unavailable."


# -------------------------------------------
# 🎨 IMAGE GENERATOR
# -------------------------------------------
def generate_image(query):
    try:
        prompt = query.lower()
        for word in ["generate", "create", "make", "draw", "image", "picture", "photo", "of"]:
            prompt = prompt.replace(word, "")
        prompt = prompt.strip()

        if not prompt:
            prompt = "futuristic abstract digital art"

        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}"
        return f"**🎨 Image Generated:** *{prompt}*\n\n![{prompt}]({url})"
    except Exception:
        return "⚠️ Image generation failed."


# -------------------------------------------
# 📝 SUMMARIZER (AI-Powered)
# -------------------------------------------
def summarizer(text):
    system = """You are an expert summarizer. Provide a clear, concise summary with:
    - Key points (bullet list)
    - Main takeaway (1 sentence)
    Keep it brief but comprehensive. Use markdown formatting."""

    return _ai_generate(system, f"Summarize the following:\n\n{text}")


# -------------------------------------------
# 🌍 TRANSLATOR (AI-Powered)
# -------------------------------------------
def translator(text):
    system = """You are a professional translator. Detect the source language automatically.
    Provide:
    - Translation
    - Source language detected
    - Any cultural notes if relevant
    Use markdown formatting."""

    return _ai_generate(system, f"Translate this: {text}")


# -------------------------------------------
# 📝 TODO MANAGER
# -------------------------------------------
def todo_manager(query, user_profile_path="user_profile.json"):
    import json

    try:
        with open(user_profile_path, "r") as f:
            user = json.load(f)
    except Exception:
        user = {"todos": []}

    todos = user.get("todos", [])
    ql = query.lower()

    # Add todo
    if any(word in ql for word in ["add todo", "add task", "remind me", "remember"]):
        task_text = query
        for prefix in ["add todo", "add task", "remind me to", "remind me", "remember to", "remember"]:
            task_text = re.sub(prefix, "", task_text, flags=re.IGNORECASE).strip()
        task_text = task_text.strip(": ").strip()

        if task_text:
            from datetime import datetime
            todos.append({
                "task": task_text,
                "done": False,
                "added": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            user["todos"] = todos
            with open(user_profile_path, "w") as f:
                json.dump(user, f, indent=4)
            return f"✅ **Todo added:** {task_text}\n\n📋 You now have **{len([t for t in todos if not t['done']])}** pending tasks."

    # Complete todo
    elif any(word in ql for word in ["complete task", "done task", "finish task", "mark done"]):
        try:
            num = int(re.search(r'\d+', query).group()) - 1
            if 0 <= num < len(todos):
                todos[num]["done"] = True
                user["todos"] = todos
                with open(user_profile_path, "w") as f:
                    json.dump(user, f, indent=4)
                return f"✅ **Completed:** ~~{todos[num]['task']}~~"
        except Exception:
            pass
        return "❌ Couldn't find that task. Use `show todos` to see your list."

    # Show todos
    elif any(word in ql for word in ["show todo", "my todo", "my task", "list task", "show task", "pending"]):
        if not todos:
            return "📋 **No todos yet!** Try: `add todo buy groceries`"

        lines = ["**📋 Your Todo List:**\n"]
        for i, t in enumerate(todos):
            status = "✅" if t["done"] else "⬜"
            lines.append(f"{i+1}. {status} {t['task']}  *({t.get('added', '')})*")

        pending = len([t for t in todos if not t["done"]])
        lines.append(f"\n**{pending}** pending | **{len(todos) - pending}** completed")
        return "\n".join(lines)

    # Clear completed
    elif "clear done" in ql or "clear completed" in ql:
        user["todos"] = [t for t in todos if not t["done"]]
        with open(user_profile_path, "w") as f:
            json.dump(user, f, indent=4)
        return "🗑️ Cleared all completed todos!"

    return None


# -------------------------------------------
# 😂 MOTIVATION / JOKES
# -------------------------------------------
def motivation(query):
    if "joke" in query.lower():
        system = "You are a comedian. Tell a short, clean, funny joke. Keep it brief."
    else:
        system = "You are a motivational coach. Provide an inspiring quote or motivational message. Keep it powerful and brief."

    return _ai_generate(system, query, max_tokens=256)


# -------------------------------------------
# 🔧 MASTER TOOL HANDLER
# -------------------------------------------
def tool_handler(q):
    ql = q.lower().strip()

    # 📝 Todo Manager (check first — high priority)
    if any(word in ql for word in ["todo", "task", "remind me", "remember", "pending"]):
        result = todo_manager(q)
        if result:
            return {"tool": "todo_manager", "output": result}

    # 🧮 Calculator
    if "calculate" in ql or "calc " in ql:
        return {"tool": "calculator", "output": calculator(q)}

    # Check for pure math expressions (e.g., "23 * 4", "100 + 50")
    if re.search(r'\d+\s*[+\-*/]\s*\d+', ql) and len(ql) < 50:
        return {"tool": "calculator", "output": calculator(q)}

    # 🌤️ Weather
    if "weather" in ql or "temperature" in ql or "climate" in ql:
        return {"tool": "weather", "output": weather(q)}

    # 📧 Email Writer
    if any(word in ql for word in ["write email", "draft email", "compose email", "email to", "write a mail", "write mail"]):
        return {"tool": "email_writer", "output": email_writer(q)}

    # 🧪 Test Case Generator
    if any(phrase in ql for phrase in ["test case", "test cases", "write test", "generate test"]):
        return {"tool": "test_case_generator", "output": test_case_generator(q)}

    # 💻 Code Generator
    if any(phrase in ql for phrase in ["write code", "generate code", "code for", "write a program", "write program", "create function", "write function"]):
        return {"tool": "code_generator", "output": code_generator(q)}

    # 🤔 Decision Maker
    if any(phrase in ql for phrase in ["should i", "decide between", "help me decide", "which is better", "compare"]):
        return {"tool": "decision_maker", "output": decision_maker(q)}

    # 🌐 Web Search
    if any(word in ql for word in ["latest", "news", "search for", "search about", "look up", "find info", "google"]):
        return {"tool": "web_search", "output": web_search(q)}

    # 📄 URL Reader
    if re.search(r'https?://', ql):
        if any(word in ql for word in ["read", "summarize", "open", "what"]):
            return {"tool": "read_url", "output": read_url(q)}

    # 🎨 Image Generator
    if any(word in ql for word in ["generate image", "create image", "draw", "make image", "picture of", "generate picture"]):
        return {"tool": "generate_image", "output": generate_image(q)}

    # 📝 Summarizer
    if any(word in ql for word in ["summarize", "summary", "tldr", "tl;dr"]):
        return {"tool": "summarizer", "output": summarizer(q)}

    # 🌍 Translator
    if any(word in ql for word in ["translate", "translation", "say in", "how to say"]):
        return {"tool": "translator", "output": translator(q)}

    # 😂 Motivation / Jokes
    if any(word in ql for word in ["motivate", "motivation", "inspire", "joke", "funny", "cheer me up"]):
        return {"tool": "motivation", "output": motivation(q)}

    return None