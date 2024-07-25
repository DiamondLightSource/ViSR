import stomp
import time
from some_event_library import SomeEvent  # Replace with your actual library and event

class MyListener(stomp.ConnectionListener):
    def on_error(self, frame):
        print('received an error:', frame.body)

    def on_message(self, frame):
        print('received a message:', frame.body)

def send_event():
    conn = stomp.Connection([('localhost', 5672)])
    conn.set_listener('', MyListener())
    conn.start()
    conn.connect('user', 'password', wait=True)

    event = SomeEvent(param1="value1", param2="value2")  # Replace with actual event data
    conn.send(body=event.json(), destination='/queue/test')

    conn.disconnect()

if __name__ == "__main__":
    send_event()
