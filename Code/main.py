from fastapi import FastAPI, WebSocket
from conversation_manager import ConversationManager
import uuid

app = FastAPI()
manager = ConversationManager()


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())

    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message")

            for token in manager.process_message_stream(session_id, user_message):
                await websocket.send_text(token)

            await websocket.send_text("[END]")

    except Exception as e:
        await websocket.close()