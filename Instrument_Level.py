from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
import threading
import time
import logging
n = 0

#This script write 0 or 1 in an instrument_status file if the instruments are generating sound

# OSC client for sending messages to Ableton
client = udp_client.SimpleUDPClient("127.0.0.1", 11000)
# Create a dispatcher
disp = dispatcher.Dispatcher()

# Register a function to handle OSC messages on address "/live/device/get/parameters/value"
def volume_handler(unused_addr, *args):
    #print("Volume of track "+str(args[-3])) #found empiricaly
    print(float(args[-3]))

    if n == 0:
        with open("instrument_status.txt", "w") as file:
            file.write(str(args[-3]))
    elif n == 1:
        with open("piano_status.txt", "w") as file:
            file.write(str(args[-3]))


disp.map("/live/device/get/parameters/value", volume_handler)

# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)
# Start the OSC server
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()

while True:
    # Request the parameters' values of the device, alternate between instruments and piano
    if n == 0 :
        client.send_message("/live/device/get/parameters/value", [2, 1])
        n = 1

    else:
        client.send_message("/live/device/get/parameters/value", [3, 2])
        n = 0

    time.sleep(0.5)

