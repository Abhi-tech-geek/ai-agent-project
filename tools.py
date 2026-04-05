# ------------------------
# CALCULATOR
# ------------------------
def calculator(expression):
    try:
        return str(eval(expression))
    except:
        return "Invalid calculation"


# ------------------------
# WEATHER
# ------------------------
def weather(city):
    import requests

    try:
        url = f"https://wttr.in/{city}?format=%t+%C"
        response = requests.get(url, timeout=5)

        response.encoding = "utf-8"   # ✅ fix encoding

        return f"Weather of {city} now - : {response.text}"

    except:
        return "⚠️ Weather service unavailable"


# ------------------------
# EMAIL WRITER
# ------------------------
def email_writer(prompt):
    return f"""
📧 Email Draft:

Subject: Regarding {prompt}

Hi,

I hope you are doing well.

{prompt}

Best Regards,
Abhinav
"""


# ------------------------
# TEST CASE GENERATOR
# ------------------------
def test_case_generator(feature):
    return f"""
🧪 Test Cases for: {feature}

1. Verify {feature} loads correctly
2. Verify valid input works
3. Verify invalid input shows error
4. Verify edge cases handled
"""


# ------------------------
# CODE GENERATOR
# ------------------------
def code_generator(prompt):
    return f"""
💻 Generated Code:

# {prompt}

def solution():
    pass
"""


# ------------------------
# DECISION MAKER
# ------------------------
def decision_maker(problem):
    return f"""
🤔 Decision Analysis:

Problem: {problem}

Pros:
- Better growth
- More opportunities

Cons:
- Risk involved

Final: Depends on your long-term goal
"""


# ------------------------
# WEB SEARCH
# ------------------------
def web_search(query):
    from duckduckgo_search import DDGS

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=3):
            results.append(f"{r['title']}: {r['body']}")

    return "\n\n".join(results)


# ------------------------
# TOOL HANDLER
# ------------------------
def tool_handler(q):
    ql = q.lower()

    if "calculate" in ql or any(op in ql for op in "+-*/"):
        return {
            "tool": "calculator",
            "output": calculator(q)
        }

    elif "weather" in ql:
        return {
            "tool": "weather",
            "output": weather(q.split("in")[-1].strip())
        }

    elif "email" in ql or "mail" in ql:
        return {
            "tool": "email_writer",
            "output": email_writer(q)
        }

    elif "test case" in ql or "testing" in ql:
        return {
            "tool": "test_case",
            "output": test_case_generator(q)
        }

    elif "code" in ql or "python" in ql:
        return {
            "tool": "code_generator",
            "output": code_generator(q)
        }


    elif "should" in ql:
        return {
            "tool": "decision_maker",
            "output": decision_maker(q)
        }

    elif "what is" in ql or "who is" in ql or "latest" in ql:
        return {
            "tool": "web_search",
            "output": web_search(q)
        }


    return None