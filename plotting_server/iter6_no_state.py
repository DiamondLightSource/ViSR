import asyncio
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from threading import Thread
from typing import Annotated

import h5py
import numpy as np
import redis
from fastapi import Depends, FastAPI, WebSocket
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# hold in redis
visr_dataset_name = "entry/instrument/detector/data"
file_writing_path = "/dls/b01-1/data/2025/cm40661-1/bluesky"
default_filename = "-Stan-March-2025.hdf"
state = {
    "filepath": file_writing_path,
    "filename": default_filename,
    "dataset_name": visr_dataset_name,
    "dset": None,
    "file": None,
    "stats_array": [],
}


def list_hdf5_tree(file_path: str) -> None:
    """Recursively lists all groups and datasets in an HDF5 file."""
    with h5py.File(file_path, "r") as f:

        def print_attrs(name, obj):
            obj_type = "Group" if isinstance(obj, h5py.Group) else "Dataset"
            print(f"{obj_type}: {name}")
            for key, value in obj.attrs.items():
                print(f"  Attribute - {key}: {value}")

        f.visititems(print_attrs)


# Example usage
# list_hdf5_tree("foo.hdf5")


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

    print(r_values, g_values, b_values, t_values)
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

    print(fractions)
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


def process_image(image: np.ndarray) -> ImageStats:
    """
    Divide the image into 3 parts, compute sums for each part, and store in a dataclass.
    """
    # print(f"processing image: {image}")
    # print(f"shape: {image.shape}")
    h, _ = image.shape[0], image.shape[1]  # Get height and width of each 2D slice

    segment_height = h // 3
    # print(f"h and segment h: {h}, {segment_height}")

    # Divide image into three parts along the height dimension
    r_sum = np.sum(image[:, :segment_height])
    g_sum = np.sum(image[:, segment_height : 2 * segment_height])
    b_sum = np.sum(image[:, 2 * segment_height :])

    # Return results as a dataclass
    return ImageStats(r=r_sum, g=g_sum, b=b_sum, total=r_sum + g_sum + b_sum)


class Settings(BaseSettings):
    hdf_path: str
    redis_host: str = "localhost"
    redis_port: int = 6379
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()


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
async def startup(settings=Depends(get_settings)):  # noqa: B008
    app.state.redis = get_redis()
    app.state.manager = manager

    print(settings)
    print(f"Starting notifier for {settings.hdf_path}")

    def start_notifier():
        observer = Observer()
        handler = EventHandler(app.state.redis, app.state.manager)
        observer.schedule(handler, settings.hdf_path, recursive=False)
        observer.start()
        observer.join()  # Keep it running

    Thread(target=start_notifier, daemon=True).start()


@app.get("/files")
async def get_files(
    redis: Annotated[dict, Depends(get_redis)],
    settings: Annotated[dict, Depends(get_settings)],
):
    # list all the files in the path
    files = [f for f in os.listdir(settings.hdf_path) if f.endswith(".hdf5")]
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
