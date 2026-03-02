from typing import Dict, List
from ollama_client import generate_stream


class ConversationManager:
    def __init__(self):
        # session_id → session data
        self.sessions: Dict[str, Dict] = {}

    def create_session(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "profile": {
                    "goal": None,
                    "experience": None,
                    "age": None,
                    "weight": None,
                    "injury": None,
                },
                "history": []
            }

    def update_profile(self, session_id: str, key: str, value):
        if session_id in self.sessions:
            self.sessions[session_id]["profile"][key] = value

    def add_to_history(self, session_id: str, role: str, content: str):
        self.sessions[session_id]["history"].append({
            "role": role,
            "content": content
        })

        # Keep only last 8 messages
        self.sessions[session_id]["history"] = \
            self.sessions[session_id]["history"][-8:]

    def build_prompt(self, session_id: str, user_message: str) -> str:
        session = self.sessions[session_id]
        profile = session["profile"]
        history = session["history"]

        system_prompt = """
You are FitGuide AI, a professional gym coaching assistant.

Rules:
- Be motivational and supportive.
- Ask clarifying questions before giving plans.
- Provide structured workout plans (sets, reps, rest).
- Do NOT give medical advice.
- If injury is mentioned, suggest consulting a doctor.
- Keep answers concise but helpful.
"""

        profile_section = f"""
User Profile:
Goal: {profile['goal']}
Experience: {profile['experience']}
Age: {profile['age']}
Weight: {profile['weight']}
Injury: {profile['injury']}
"""

        history_section = "\nRecent Conversation:\n"
        for msg in history:
            history_section += f"{msg['role'].capitalize()}: {msg['content']}\n"

        current_message_section = f"\nCurrent User Message:\n{user_message}\n"

        full_prompt = (
            system_prompt +
            profile_section +
            history_section +
            current_message_section
        )

        return full_prompt

    def process_message_stream(self, session_id: str, user_message: str):
        self.create_session(session_id)
        self.add_to_history(session_id, "user", user_message)

        prompt = self.build_prompt(session_id, user_message)

        full_response = ""

        for token in generate_stream(prompt):
            full_response += token
            yield token

        self.add_to_history(session_id, "assistant", full_response)