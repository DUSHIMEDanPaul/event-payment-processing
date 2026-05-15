import threading
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websocket_manager import manager
from rabbitmq_consumer import start_rabbitmq_consumer

app = FastAPI(title="Notification Service")

@app.on_event("startup")
async def startup_event():
    # Start RabbitMQ consumer in a separate thread
    loop = asyncio.get_event_loop()
    thread = threading.Thread(target=start_rabbitmq_consumer, args=(loop,), daemon=True)
    thread.start()

@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo for testing
            await websocket.send_text(f"Message received from client {client_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
