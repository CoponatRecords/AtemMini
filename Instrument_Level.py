from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
import threading
import time
import logging

'''
This script writes in an instrument_status.txt file and piano_status.txt the current audio level of the tracks.
Works with an envelope follower linked to a utility's gain on the third (group all instrument) and fourth (piano with a 
vst) tracks of ableton

Ableton needs to have AbletonOSC installed : https://github.com/ideoforms/AbletonOSC
To run this script : right-click, run 'instrument_level'
'''

# OSC client for sending messages to Ableton
client = udp_client.SimpleUDPClient("127.0.0.1", 11000)
# Create a dispatcher
disp = dispatcher.Dispatcher()


# Register a function to handle OSC messages on address "/live/device/get/parameters/value"
def volume_handler(*args):
    # print("Volume of track "+str(args[-3])) #found empiricaly

    if n == 0:
        with open("voice_status.txt", "w") as file:
            file.write(str(args[-3]))
            print('voice_status\t- ' + str(float(args[-3])))

    elif n == 1:
        with open("piano_status.txt", "w") as file:
            file.write(str(args[-3]))
            print('Piano\t- ' + str(float(args[-3])))
    elif n == 2:
        with open("instrument_status.txt", "w") as file:
            file.write(str(args[-3]))
            print('instru\t- ' + str(float(args[-3])))


disp.map("/live/device/get/parameters/value", volume_handler)
# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)
# Start the OSC server
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()

n = 0
while True:
    # Request the parameters' values of the device, alternate between all instruments and just piano
    if n == 0:
        client.send_message("/live/device/get/parameters/value", [3, 2])
        n = 1
    elif n == 1:
        client.send_message("/live/device/get/parameters/value", [2, 1])
        n = 2
    elif n == 2:
        client.send_message("/live/device/get/parameters/value", [1, 1])
        n = 0

    time.sleep(0.5)
