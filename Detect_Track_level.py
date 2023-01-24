from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
import time
import threading
import time
import logging

# OSC client for sending messages to Ableton
client = udp_client.SimpleUDPClient("127.0.0.1", 11000)
# Create a dispatcher
disp = dispatcher.Dispatcher()

iteration = 0

# Register a function to handle OSC messages on address "/live/device/get/parameters/value"
def volume_handler(unused_addr, *args):
    print("Volume of track "+str(args[-3])) #found empiricaly
    logging.basicConfig(filename='volume_instruments.log', level=logging.INFO)
    logging.info("Volume of track "+str(args[-3]))
    if iteration>10:
        with open("volume_instruments.log", "w") as file:
            file.truncate(0)

disp.map("/live/device/get/parameters/value", volume_handler)

# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)
# Start the OSC server
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()

while True:
    # Request the parameters' values of the device at index 1
    client.send_message("/live/device/get/parameters/value", [2, 1])
    iteration+=1
    # Wait for 0.1 second
    time.sleep(0.1)

server.shutdown()
print("Done")