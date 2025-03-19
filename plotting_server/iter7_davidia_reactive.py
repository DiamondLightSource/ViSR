import asyncio
import json

import h5py
import numpy as np
import stomp
from davidia.main import create_app
from davidia.models.messages import Aspect, ImageData, ImageDataMessage, PlotConfig
from event_model import StreamDatum, StreamResource
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket

# NOTE this defines a Davidia streaming app
app = create_app()


# CORS setup for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""
overall plan.
1. listen to stomp messages
2. parse the messages to get file path
3. from filepath parse data into davidia classes (ImageStats?)
4. let Davidia send that data over websocket to the client
"""

state = {
    "filepath": "",
}

active_websockets = set()


async def send_to_clients(image_data: ImageDataMessage):
    """Send the transformed image data to all connected WebSocket clients."""
    message_json = json.dumps(
        image_data.model_dump()
    )  # FastAPI's Pydantic models support `model_dump`
    for websocket in active_websockets:
        await websocket.send_text(message_json)


def tranform_dataset_into_dto(dataset: h5py.Dataset) -> ImageDataMessage:
    x_values = np.arange(dataset.shape[1])
    y_values = np.arange(dataset.shape[0])
    # todo fix the values errror
    data = ImageData(values=dataset, aspect=Aspect.equal)
    plot_config = PlotConfig(
        x_label="x-axis",
        y_label="y-axis",
        x_values=x_values,
        y_values=y_values,
        title="image benchmarking plot",
    )
    return ImageDataMessage(im_data=data, plot_config=plot_config)


class STOMPListener(stomp.ConnectionListener):
    def on_error(self, frame):
        print(f"Error: {frame.body}")

    def on_message(self, frame):
        print(f"Received message: {frame.body}")
        message = frame.body
        resource = StreamResource(message)
        specific_slice = StreamDatum(message)
        print(f"Resource: {resource}")
        print(f"Specific Slice: {specific_slice}")
        # todo learn to read h5py files based on that description,
        # need empirical data here
        path = resource["uri"]
        file = h5py.File(path, "r")
        dataset = file["data"]

        # Check if it is a dataset before transforming
        if not isinstance(dataset, h5py.Dataset):
            print("Error: 'data' is not a dataset.")
            return

        image_data = tranform_dataset_into_dto(dataset)
        # todo add a connection so that the davidia app will send the item

        # Send to WebSocket clients
        asyncio.run(send_to_clients(image_data))  # Ensure async execution


def start_stomp_listener():
    conn = stomp.Connection([("localhost", 5672)])
    conn.set_listener("", STOMPListener())
    try:
        conn.connect("user", "password", wait=True)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
    # todo adapt the correct topic, maybe from env vars
    conn.subscribe(destination="/queue/test", id=1, ack="auto")


if __name__ == "__main__":
    from threading import Thread

    import uvicorn

    thread_for_stomp = Thread(target=start_stomp_listener)

    thread_for_stomp.start()
    uvicorn.run(app)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for clients to receive live image data."""
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_websockets.remove(websocket)
