from typing import Dict, List
from ollama_client import generate_stream
import re


class ConversationManager:
    def __init__(self):
        # session_id → session data
        self.sessions: Dict[str, Dict] = {}

    PROFILE_UPDATE_PATTERN = re.compile(
        r"\[PROFILE_UPDATE:\s*([^]]+)\]",
        re.IGNORECASE,
    )
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

    def extract_and_update_profile(self, session_id: str, assistant_message: str) -> str:
        """Extract profile updates from assistant message and update session profile."""
        session = self.sessions.get(session_id)
        if not session:
            return assistant_message

        match = self.PROFILE_UPDATE_PATTERN.search(assistant_message)
        if not match:
            return assistant_message

        updates_str = match.group(1).strip()
        print(f"Profile update detected: {updates_str}")

        # Parse key=value pairs
        updates = {}
        for pair in updates_str.split(','):
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip().lower()
                value = value.strip()

                # Map to our profile fields
                if key in ['goal', 'experience', 'age', 'weight', 'injury']:
                    updates[key] = value

        # Update profile
        if updates:
            for key, value in updates.items():
                old_value = session["profile"][key]
                session["profile"][key] = value
                print(f"Updated {key}: {old_value} → {value}")

            # Remove the profile update marker from the message
            cleaned_message = self.PROFILE_UPDATE_PATTERN.sub("", assistant_message).strip()
            return cleaned_message

        return assistant_message
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

Profile extraction policy:
- Actively extract user profile information from conversation.
- When you learn new profile details, include them in your response using this format:
  [PROFILE_UPDATE: key=value, key2=value2]
- Extract: goal, experience, age, weight, injury
- Examples: [PROFILE_UPDATE: age=25, weight=75kg, goal=build muscle]
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

        # Extract and apply any profile updates from the response
        cleaned_response = self.extract_and_update_profile(session_id, full_response)

        # Save the cleaned response (without profile update markers) to history
        self.add_to_history(session_id, "assistant", cleaned_response)
