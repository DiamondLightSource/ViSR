from fastapi import FastAPI, WebSocket
import stomp
import json
from event_model import StreamData, StreamDatum

app = FastAPI()
clients = set()

class STOMPListener(stomp.ConnectionListener):
    def on_error(self, frame):
        print(f'Error: {frame.body}')

    def on_message(self, frame):
        print(f'Received message: {frame.body}')
        message = frame.body
        for client in clients:
            client.send_json(json.loads(message))

@app.websocket("/ws/colors")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        clients.remove(websocket)

def start_stomp_listener():
    conn = stomp.Connection([('localhost', 5672)])
    conn.set_listener('', STOMPListener())
    conn.start()
    conn.connect('user', 'password', wait=True)
    conn.subscribe(destination='/queue/test', id=1, ack='auto')

if __name__ == "__main__":
    import uvicorn
    from threading import Thread

    # Start the STOMP listener in a separate thread
    thread = Thread(target=start_stomp_listener)
    thread.start()

    uvicorn.run(app, host="0.0.0.0", port=8000)
