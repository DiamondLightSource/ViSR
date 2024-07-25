import random
import numpy as np
import time
from fastapi import FastAPI, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
import io
import asyncio


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "ws://localhost:5174"],  # React dev server
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
    plt.savefig(buf, format="png")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Simulating data generation
            now = time.time()
            data = {"time": now, "value": random.random()}
            await websocket.send_json(data)
            await asyncio.sleep(0.01)  # 100 Hz rate
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()



# Generate 10,000 random integers between 0 and 255
def generate_rgb_array(size=10000):
    return np.random.randint(0, 256, size=size, dtype=np.uint8)

# Initialize RGB arrays
r_array = generate_rgb_array()
g_array = generate_rgb_array()
b_array = generate_rgb_array()

@app.websocket("/ws/colors")
async def colors_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Simulate data generation
            now = time.time()
            # Compute total of RGB values
            r_total = np.sum(r_array)
            g_total = np.sum(g_array)
            b_total = np.sum(b_array)
            total = r_total + g_total + b_total

            # Generate intensity value as a random 8-bit integer
            intensity = random.randint(0, 255)

            # Create JSON data format
            # todo decide if 1 message parsed on the frontend or 3 different messages
            data = {
                "c": {
                    "r": r_total,
                    "g": g_total,
                    "b": b_total,
                    "total": total
                },
                "i": intensity
            }

            # Send JSON data
            await websocket.send_json(data)
            await asyncio.sleep(0.1)  # Emit every 100 ms (10 Hz)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()
