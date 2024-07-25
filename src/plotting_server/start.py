from fastapi import FastAPI, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
import io
import asyncio

app = FastAPI()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/plot/")
async def get_plot():
    # Generate a Matplotlib plot
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_title("Sample Plot")

    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Simulating data generation
            data = {"time": time.time(), "value": random.random()}
            await websocket.send_json(data)
            await asyncio.sleep(0.1)  # 10 Hz rate
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()