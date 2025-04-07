import asyncio
import json
from pathlib import Path

import stomp

CHANNEL = "/topic/public.worker.event"


class STOMPListener(stomp.ConnectionListener):
    def on_error(self, frame):
        print(f"Error: {frame.body}")

    # todo need to parse the message and start streaming a file if needed https://docs.h5py.org/en/latest/quick.html
    def on_message(self, frame):
        message = frame.body
        print(f"Received message: {message}")


def start_stomp_connection():
    conn = stomp.Connection([("localhost", 5672)])
    conn.set_listener("", STOMPListener())
    # conn.connect("user", "password", wait=True)
    conn.connect("user", "password", wait=True)
    conn.connect(wait=True)
    return conn


async def replay_events_from_json(
    json_path: Path, conn: stomp.Connection, delay: float = 0.05
):
    with open(json_path) as f:
        data = json.load(f)

    events = data.get("events", [])
    for event in events:
        print(f"🔁 Emitting: {event['name']} - {event.get('doc', {}).get('uid', '')}")
        message = json.dumps(event)
        conn.send(destination=CHANNEL, body=message)
        print(f"🔁 Sent event to STOMP: {message}")
        await asyncio.sleep(delay)


async def main():
    conn = start_stomp_connection()
    await replay_events_from_json(Path("events-to-emit-6.json"), conn)
    conn.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
