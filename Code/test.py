from conversation_manager import ConversationManager

manager = ConversationManager()

session_id = "test_user"

while True:
    user_input = input("You: ")
    response = manager.process_message(session_id, user_input)
    print("Bot:", response)