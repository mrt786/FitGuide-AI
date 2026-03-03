from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from conversation_manager import ConversationManager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
manager = ConversationManager()

app.mount("/static", StaticFiles(directory="Frontend/"), name="static")

@app.get("/")
async def root():
    return FileResponse("Frontend/index.html")

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())
    logger.info(f"New WebSocket connection: {session_id}")

    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message")

            if not user_message:
                await websocket.send_text("[END]")
                continue

            # Stream tokens one by one
            for token in manager.process_message_stream(session_id, user_message):
                await websocket.send_text(token)
                await asyncio.sleep(0)  # allow event loop switch

            await websocket.send_text("[END]")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
        await websocket.close()