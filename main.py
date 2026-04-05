from multi_agent import multi_agent_with_tools, setup_user
from voice import listen, speak

setup_user()

while True:
    q = listen()

    if q.lower() == "exit":
        speak("Bye bhai")
        break

    res = multi_agent_with_tools(q)
    print(res)
    speak(res)