from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
import time
import threading
import time

# OSC client for sending messages to Ableton
client = udp_client.SimpleUDPClient("127.0.0.1", 11000)

# Create a dispatcher
disp = dispatcher.Dispatcher()

# Register a function to handle OSC messages on address "/live/device/get/parameters/value"
def volume_handler(unused_addr, *args):
    print("Volume of track "+str(args[-3])) #found empiricaly

disp.map("/live/device/get/parameters/value", volume_handler)

# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)
# Start the OSC server
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()

while True:
    # Request the parameters' values of the device at index 2
    client.send_message("/live/device/get/parameters/value", [0, 2])
    # Wait for 1 second
    time.sleep(0.1)

server.shutdown()
print("Done")