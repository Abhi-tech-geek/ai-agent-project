import pyttsx3

engine = pyttsx3.init()

# 🔥 Voice settings (IMPORTANT)
engine.setProperty('rate', 170)   # speed (default ~200)
engine.setProperty('volume', 1)   # max volume

voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)  # change 0/1 for male/female


def speak(text):
    print("AI बोल रहा है...")
    engine.say(text)
    engine.runAndWait()


def listen():
    return input("You (type): ")