import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
import pyinotify
from fastapi import FastAPI, WebSocket


@dataclass
class ImageStats:
    r: int
    g: int
    b: int
    total: int


# FastAPI app setup
app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    EventHandler.websocket = websocket


class EventHandler(pyinotify.ProcessEvent):
    stats_array: list[ImageStats] = []
    websocket: WebSocket | None = None
    dset: h5py.Dataset | None = None
    f: h5py.File

    def monitor_dataset(self, filename: str, datasetname: str):
        logging.info("Opening file %s", filename)
        self.f = h5py.File(filename, "r", libver="latest", swmr=True)
        logging.debug(f"Looking up dataset {datasetname}")
        if self.f[datasetname]:
            self.dset = self.f[datasetname]  # type: ignore

        self.get_dset_shape()

    def get_dset_shape(self) -> tuple:
        if self.dset is None:
            return (0, 0)
        logging.debug("Refreshing dataset")
        self.dset.refresh()

        logging.debug("Getting shape")
        shape = self.dset.shape
        logging.info(f"Read data shape: {str(shape)}")
        return shape

    def read_dataset(self, latest: str) -> None:
        if self.dset:
            logging.info(f"Reading out dataset [{latest}]")
            self.dset[latest:]
        else:
            logging.warning(f"Could not find dataset [{latest}]")

    def process_IN_CREATE(self, event):
        print(f"File created: {event.pathname}")

    def process_IN_MODIFY(self, event):
        print(f"File modified: {event.pathname}")
        # Mock loading image from the file
        new_image = np.ones((4, 1216, 1936), dtype=np.uint8) * np.random.randint(1, 10)
        variance = process_and_append(new_image, EventHandler.stats_array)
        asyncio.create_task(self.send_variance(variance))

    async def send_variance(self, variance):
        if EventHandler.websocket:
            await EventHandler.websocket.send_json({"variance": variance.tolist()})


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
    Process a new image, append its stats to the stats array,
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


# Example usage with pyinotify
if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s  %(levelname)s\t%(message)s", level=logging.INFO
    )

    filename = "0.hdf"
    filepath: Path = Path("/tmp")
    dataset_name = "['entry']['instrument']['detector']['data']"

    # Initialize inotify watcher
    wm = pyinotify.WatchManager()
    handler = EventHandler()
    handler.monitor_dataset(filename, datasetname=dataset_name)
    notifier = pyinotify.Notifier(wm, handler)
    mask = pyinotify.IN_CREATE | pyinotify.IN_MODIFY
    wm.add_watch(filepath, mask, rec=False)

    print("Watching /tmp for file changes...")
    notifier.loop()
