import asyncio
import json
from threading import Thread
from typing import Annotated

import redis
from fastapi import Depends, FastAPI, WebSocket
from plotting_server.iter6_logic import process_image
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# hold redis in the Depends call from fastapi

def get_redis() -> redis.Redis:
    return redis.Redis(host="localhost", port=6379)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    async def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def broadcast(self, message: dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)


manager = ConnectionManager()


class EventHandler(FileSystemEventHandler):
    def __init__(self, redis, manager):
        self.redis = redis
        self.manager = manager

    def on_modified(self, event: FileSystemEvent):
        print(f"File modified: {event.src_path}")

        # Read image data and store in Redis
        image_data = process_image(event.src_path)
        asyncio.create_task(self.redis.set("latest_image", json.dumps(image_data)))

        # Broadcast update to WebSocket clients
        asyncio.create_task(self.manager.broadcast({"image": image_data}))


app = FastAPI()
app.state.redis = None


@app.on_event("startup")
async def startup():
    app.state.redis = await get_redis()
    app.state.manager = manager

    def start_notifier():
        observer = Observer()
        handler = EventHandler(app.state.redis, app.state.manager)
        observer.schedule(handler, "/path/to/watch", recursive=False)
        observer.start()
        observer.join()  # Keep it running

    Thread(target=start_notifier, daemon=True).start()

@app.get("/files")
async def get_files(redis: Annotated[dict, Depends(get_redis)]):
    import os
    # get path from redis
    path = redis.get("path")
    # list all the files in the path
    files: list[str] = os.listdir(path)
    return {"files": files}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from {client_id}: {data}")
    except Exception:
        pass
    finally:
        await manager.disconnect(client_id)


@app.get("/image")
async def get_latest_image():
    redis = app.state.redis
    image_data = await redis.get("latest_image")
    return json.loads(image_data) if image_data else {"error": "No image found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
