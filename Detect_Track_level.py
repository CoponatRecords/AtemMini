from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
import concurrent.futures

# OSC client for sending messages to Ableton
client = udp_client.SimpleUDPClient("127.0.0.1", 11000)

# Request the volume of the first track
client.send_message("/live/device/get/parameters/value", [0,2])

# Create a dispatcher
disp = dispatcher.Dispatcher()

# Register a function to handle OSC messages on address "/live/volume"
def volume_handler(unused_addr, *args):
    for name, value in zip(args[0::2], args[1::2]):
        print("Parameter name: {0}, value: {1}".format(name, value))

disp.map("/live/device/get/parameters/value", volume_handler)

# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)
# Start the OSC server
server.serve_forever()
server.shutdown()
print("Done")
