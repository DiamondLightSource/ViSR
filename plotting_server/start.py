import asyncio
import io
import random
import time

import matplotlib.pyplot as plt
import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# from event_model import StreamData, StreamDatum

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "ws://localhost:5174",
        "http://localhost:5173",
        "ws://localhost:5173"
    ],  # React dev server
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

# # Normalize color data
# r_max = np.max(r_array)
# g_max = np.max(g_array)
# b_max = np.max(b_array)

# # Avoid division by zero if max is zero
# r_max = r_max if r_max != 0 else 1
# g_max = g_max if g_max != 0 else 1
# b_max = b_max if b_max != 0 else 1

# # Normalize the arrays
# r_normalized = r_array / r_max * 255
# g_normalized = g_array / g_max * 255
# b_normalized = b_array / b_max * 255

interval = 0.6
# 0.1 to Emit every 100 ms (10 Hz)


@app.websocket("/ws/colors")
async def colors_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("got a request")
    try:
        while True:
            for r, g, b in zip(r_array, g_array, b_array, strict=False):
                total = r + g + b

                # Convert NumPy integers to standard Python integers
                r = int(r)
                g = int(g)
                b = int(b)
                total = int(total)
                # todo total will be histagrammed
                # print(r,g,b)

                # Create JSON data format
                red_data = {"c": "r", "i": r}
                green_data = {"c": "g", "i": g}
                blue_data = {"c": "b", "i": b}
                total_data = {"c": "t", "i": total}

                for data in [red_data, green_data, blue_data, total_data]:
                    # Send JSON data
                    await websocket.send_json(data)
                await asyncio.sleep(interval)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("closing the websocket")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
