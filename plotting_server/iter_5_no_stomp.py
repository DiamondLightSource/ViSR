import asyncio
import json
from dataclasses import dataclass

import h5py
import numpy as np
import pyinotify
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# visr_dataset_name = "['entry']['instrument']['detector']['data']"
visr_dataset_name = "entry/instrument/detector/data"


@dataclass
class ImageStats:
    r: np.uint64
    g: np.uint64
    b: np.uint64
    total: np.uint64


def calculate_fractions(
    stats_list: list[ImageStats],
) -> list[tuple[float, float, float, float]]:
    fractions = []

    # Extract all r, g, b, t values from the stats_list
    r_values = [stat.r for stat in stats_list]
    g_values = [stat.g for stat in stats_list]
    b_values = [stat.b for stat in stats_list]
    t_values = [stat.total for stat in stats_list]

    # Find min and max for each of the properties (r, g, b, t)
    r_min, r_max = min(r_values), max(r_values)
    g_min, g_max = min(g_values), max(g_values)
    b_min, b_max = min(b_values), max(b_values)
    t_min, t_max = min(t_values), max(t_values)

    # If any property min == max, fractions for that property will be 0
    if r_min == r_max:
        r_fractions = [0] * len(stats_list)
    else:
        r_fractions = [(stat.r - r_min) / (r_max - r_min) for stat in stats_list]

    if g_min == g_max:
        g_fractions = [0] * len(stats_list)
    else:
        g_fractions = [(stat.g - g_min) / (g_max - g_min) for stat in stats_list]

    if b_min == b_max:
        b_fractions = [0] * len(stats_list)
    else:
        b_fractions = [(stat.b - b_min) / (b_max - b_min) for stat in stats_list]

    if t_min == t_max:
        t_fractions = [0] * len(stats_list)
    else:
        t_fractions = [(stat.total - t_min) / (t_max - t_min) for stat in stats_list]

    # Combine fractions for each property into a tuple for each entry
    for i in range(len(stats_list)):
        fractions.append(
            (r_fractions[i], g_fractions[i], b_fractions[i], t_fractions[i])
        )

    return fractions


# ✅ Pydantic model for API response (converts np.uint64 to int)
class ImageStatsDTO(BaseModel):
    r: float
    g: float
    b: float
    total: float

    @classmethod
    def from_image_stats(cls, stats: ImageStats):
        """Converts ImageStats (dataclass) to ImageStatsDTO (Pydantic)"""
        return cls(
            r=float(stats.r),
            g=float(stats.g),
            b=float(stats.b),
            total=float(stats.total),
        )

    @classmethod
    def from_array(cls, list_of_floats: list[float]):
        """Converts ImageStats (dataclass) to ImageStatsDTO (Pydantic)"""
        return cls(
            r=float(list_of_floats[0]),
            g=float(list_of_floats[1]),
            b=float(list_of_floats[2]),
            total=float(list_of_floats[3]),
        )


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
    "filepath": "/dls/b01-1/data/2025/cm40661-1/bluesky",
    "filename": "0.hdf",
    "dataset_name": visr_dataset_name,
    "dset": None,
    "file": None,
    "stats_array": [],
}

clients = set()

# full_path = f"{state['filepath']}/{state['filename']}"
# print(f"full path: {full_path}")
# with h5py.File(full_path, "r", libver="latest", swmr=True) as f:
#     state["dset"] = f[visr_dataset_name]


@app.websocket("/ws/data")
async def websocket_endpoint(websocket: WebSocket):
    EventHandler.websocket = websocket
    if not state["dset"]:
        return
    await websocket.accept()
    clients.add(websocket)
    data_points: np.ndarray = state["dset"]
    try:
        while True:
            # Loop through each batch of data points
            for i in range(1, len(data_points) + 1):
                raw_data: np.ndarray = state["dset"][
                    -i:
                ]  # Shape (latest_n_reads, 1216, 1936, 3)
                print(f"raw data shape: {raw_data.shape}")

                stats_list = [(process_image(img)) for img in raw_data]
                print(f"stats list: {stats_list}")
                fractions = calculate_fractions(stats_list)
                # Send the fractions to the frontend
                print(f"fractions: {fractions}")
                await websocket.send(json.dumps(fractions))
                # Wait for a small interval before sending the next batch
                await asyncio.sleep(1)  # You can adjust the sleep time as needed
            # Send an empty array to indicate end of batch
            await websocket.send(json.dumps([]))
            await asyncio.sleep(1)  # Wait before starting a new round of data
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        clients.remove(websocket)


@app.post("/set_dataset/")
def set_dataset(
    filepath: str | None = None,
    filename: str | None = None,
    dataset_name: str | None = None,
):
    state["filepath"] = filepath or state["filepath"]
    state["filename"] = filename or state["filename"]
    state["dataset_name"] = dataset_name or state["dataset_name"]
    print(state)
    dataset_name = dataset_name or state["dataset_name"]

    try:
        full_path = f"{state['filepath']}/{state['filename']}"
        print(f"full path: {full_path}")
        state["file"] = h5py.File(full_path, "r", libver="latest", swmr=True)
        if dataset_name in state["file"]:
            print(dataset_name)
            print(state["file"]["entry"])
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


def is_serializable(value):
    try:
        json.dumps(value)
        return True
    except (TypeError, OverflowError):
        return False


def filter_serializable(data):
    return {k: v for k, v in data.items() if is_serializable(v)}


@app.get("/state")
def get_state():
    return filter_serializable(state)


@app.get("/groups")
def get_groups():
    f = h5py.File(f"{state['filepath']}/{state['filename']}")
    return {"groups": list(f.keys())}


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


@app.get("/read_dataset/", response_model=list[ImageStatsDTO])
def read_dataset(latest_n_reads: int):
    if state["dset"] is None:
        raise HTTPException(status_code=404, detail="Dataset not initialized")

    try:
        # ✅ Slice the last `latest_n_reads` images
        raw_data: np.ndarray = state["dset"][
            -latest_n_reads:
        ]  # Shape (latest_n_reads, 1216, 1936, 3)
        print(f"raw data shape: {raw_data.shape}")

        print(raw_data)
        # ✅ Process each image and convert to DTO
        # that was for debugging
        # for img in raw_data:
        #     print(img)
        #     procesed = process_image(img)
        #     print(procesed)
        #     d = ImageStatsDTO.from_image_stats(procesed)
        #     print(d)
        stats_list = [(process_image(img)) for img in raw_data]
        print(f"stats list: {stats_list}")
        fractions_list = calculate_fractions(stats_list)
        print(f"nice fractions: {fractions_list}")
        final_list = [ImageStatsDTO.from_array(a) for a in fractions_list]
        print(f"final list: {final_list}")

        print(f"stats: {stats_list}")
        return final_list  # ✅ FastAPI will return JSON array
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read dataset: {str(e)}"
        ) from e


@app.post("/demo")
def demo():
    """all the things to start the demo: query blueapi to start the loaded plan and arrange all the bits to work together."""
    pass
    # blueapi_url = "https://b01-1-blueapi.diamond.ac.uk/"
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
        t = asyncio.create_task(self.send_variance(variance))
        asyncio.gather(t)

    async def send_variance(self, variance):
        if self.websocket:
            await self.websocket.send_json({"variance": variance.tolist()})
        else:
            raise ConnectionError("eventhandler does not have a configured websocket")


def process_image(image: np.ndarray) -> ImageStats:
    """
    Divide the image into 3 parts, compute sums for each part, and store in a dataclass.
    """
    print(f"processing image: {image}")
    print(f"shape: {image.shape}")
    h, _ = image.shape[0], image.shape[1]  # Get height and width of each 2D slice

    segment_height = h // 3
    print(f"h and segment h: {h}, {segment_height}")

    # Divide image into three parts along the height dimension
    r_sum = np.sum(image[:, :segment_height])
    g_sum = np.sum(image[:, segment_height : 2 * segment_height])
    b_sum = np.sum(image[:, 2 * segment_height :])

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
    # todo add total calculation - is it after the variance or before?

    thread.start()
    uvicorn.run(app, port=8002)
