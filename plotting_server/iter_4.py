import asyncio
import json
from dataclasses import dataclass

import h5py
import numpy as np
import pyinotify
import stomp
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware


@dataclass
class ImageStats:
    r: int
    g: int
    b: int
    total: int


app = FastAPI()

# CORS setup for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state = {
    "filepath": None,
    "filename": None,
    "dataset_name": None,
    "dset": None,
    "file": None,
    "stats_array": [],
}

clients = set()


class STOMPListener(stomp.ConnectionListener):
    def on_error(self, frame):
        print(f"Error: {frame.body}")

    def on_message(self, frame):
        print(f"Received message: {frame.body}")
        message = frame.body
        # todo here parse the message to get the new filepath - or maybe it's hardcoded?
        # todo parse depending on the event_model types
        for client in clients:
            client.send_json(json.loads(message))


@app.websocket("/ws/colors")
async def websocket_endpoint(websocket: WebSocket):
    EventHandler.websocket = websocket
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
    conn = stomp.Connection([("localhost", 5672)])
    conn.set_listener("", STOMPListener())
    conn.connect("user", "password", wait=True)
    # todo adapt the correct topic
    conn.subscribe(destination="/queue/test", id=1, ack="auto")


@app.post("/set_dataset/")
def set_dataset(filepath: str, filename: str, dataset_name: str):
    state["filepath"] = filepath
    state["filename"] = filename
    state["dataset_name"] = dataset_name

    try:
        full_path = f"{filepath}/{filename}"
        state["file"] = h5py.File(full_path, "r", libver="latest", swmr=True)
        if dataset_name in state["file"]:
            state["dset"] = state["file"][dataset_name]
        else:
            raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to set dataset: {str(e)}"
        ) from e

    return {
        "message": "Dataset set successfully",
        "shape": state["dset"].shape if state["dset"] else None,  # type: ignore
    }


@app.get("/get_dataset_shape/")
def get_dataset_shape():
    if state["dset"] is None:
        raise HTTPException(status_code=404, detail="Dataset not initialized")
    try:
        state["dset"].refresh()
        shape = state["dset"].shape
        return {"shape": shape}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get dataset shape: {str(e)}"
        ) from e


@app.get("/read_dataset/")
def read_dataset(latest: int):
    if state["dset"] is None:
        raise HTTPException(status_code=404, detail="Dataset not initialized")
    try:
        data = state["dset"][latest:]
        return {"data": data.tolist()}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read dataset: {str(e)}"
        ) from e


@app.post("/demo")
def demo():
    """all the things to start the demo: query blueapi to start the loaded plan and arrange all the bits to work together."""
    blueapi_url = "https://b01-1-blueapi.diamond.ac.uk/"
    # POST request to the correct plan with the right params /tasks
    # example json body: { "name": "count", "params": { "detectors": [ "x" ] } }
    # reset the state
    # /worker/task PUT request
    # websocket send reset too


class EventHandler(pyinotify.ProcessEvent):
    websocket: WebSocket | None = None

    def process_IN_CREATE(self, event):
        print(f"File created: {event.pathname}")

    def process_IN_MODIFY(self, event):
        print(f"File modified: {event.pathname}")
        state["dset"].id.refresh()
        # Mock loading image from the file
        # todo read in the new file looking for the new array
        # dataset will be a 3d array
        new_image = state["dset"][:-1]
        variance = process_and_append(new_image, state["stats_array"])
        asyncio.create_task(self.send_variance(variance))

    async def send_variance(self, variance):
        if self.websocket:
            await self.websocket.send_json({"variance": variance.tolist()})
        else:
            raise ConnectionError("eventhandler does not have a configured websocket")


def process_image(image: np.ndarray) -> ImageStats:
    """
    Divide the image into 3 parts, compute sums for each part, and store in a dataclass.
    """
    h, _ = image.shape[1], image.shape[2]  # Get height and width of each 2D slice
    segment_height = h // 3

    # Divide image into three parts along the height dimension
    r_sum = np.sum(image[:, :segment_height, :])
    g_sum = np.sum(image[:, segment_height : 2 * segment_height, :])
    b_sum = np.sum(image[:, 2 * segment_height :, :])

    # Return results as a dataclass
    return ImageStats(r=r_sum, g=g_sum, b=b_sum, total=r_sum + g_sum + b_sum)


def process_and_append(image: np.ndarray, stats_array: list) -> np.ndarray:
    """
    Process a new image, append its stats to the stats array
    and calculate the variance array.
    """
    # Process the new image
    stats = process_image(image)
    stats_array.append(stats)

    # Extract r, g, b values from all ImageStats objects in the stats array
    r_values = np.array([d.r for d in stats_array])
    g_values = np.array([d.g for d in stats_array])
    b_values = np.array([d.b for d in stats_array])

    # Calculate min and max for r, g, b
    r_min, r_max = np.min(r_values), np.max(r_values)
    g_min, g_max = np.min(g_values), np.max(g_values)
    b_min, b_max = np.min(b_values), np.max(b_values)

    # Compute variance (max - min) normalized by max
    variance_array = np.array(
        [
            (r_max - r_min) / r_max if r_max != 0 else 0,
            (g_max - g_min) / g_max if g_max != 0 else 0,
            (b_max - b_min) / b_max if b_max != 0 else 0,
        ]
    )

    return variance_array


def start_notifier_loop():
    wm = pyinotify.WatchManager()
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    mask = pyinotify.IN_CREATE | pyinotify.IN_MODIFY  # type: ignore
    path = "/tmp"
    wm.add_watch(path, mask)

    print(f"Watching {path} for file changes...")
    notifier.loop()


if __name__ == "__main__":
    from threading import Thread

    import uvicorn

    thread = Thread(target=start_notifier_loop)
    thread_for_stomp = Thread(target=start_stomp_listener)
    # todo add total calculation - is it after the variance or before?

    thread.start()
    thread_for_stomp.start()
    uvicorn.run(app)
