'''
Automatic Scene Switcher for Atem Mini

ToDo :
    add  gui
    regroup both scripts on one start button
'''

'''
This script reads the instrument_status.txt file and piano_status.txt to switch cameras
The Atem mini has to be on and connected through ethernet. Check the connection status with the "Atem Setup" app.
The Instrument_Level script has to be on 
Ableton needs to have AbletonOSC installed : https://github.com/ideoforms/AbletonOSC

To run this script : right-click, run 'main'

'''
from ppadb.client import Client as AdbClient
from pythonosc import dispatcher, osc_server, udp_client

import PyATEMMax
import random
import threading
import time


'''
This script writes in an instrument_status.txt file and piano_status.txt the current audio level of the tracks.
Works with an envelope follower linked to a utility's gain on the third (group all instrument) and fourth (piano with a 
vst) tracks of ableton

Ableton needs to have AbletonOSC installed : https://github.com/ideoforms/AbletonOSC
To run this script : right-click, run 'instrument_level'
'''
#used to add color in terminal
CRED_RED = '\033[91m'
CRED_GREEN = '\033[42m'
CRED_BLUE= '\033[34m'
CRED_BLUE_2= '\033[44m'
CRED_GREEN_2 = '\033[92m'
CRED_ORANGE = '\033[43m'
CEND= '\033[0m'

#Entrées Atem mini:

zoom = 1
camera_face = 2
g_angle = 3
camera_drums = 4

#starting cam
last_cam = 2

#if ronin not connected: put ronin = False
ronin = False
if not ronin:
    print("No Ronin in the script")
def current_time():
    '''
    :return: time in hh:mm:ss format
    '''
    t = time.localtime()
    return str(time.strftime("%H:%M:%S", t)+' ')

#time to wait before trying to switch cameras
sleep_time = 10

switcher = PyATEMMax.ATEMMax()
#Functions to communicate with the Atem Mini
def connection_to_switcher():
    '''
    :return: connects to the switcher
    '''
    # Connect
    atem_mini_ip = "192.168.0.124"

    print(current_time()+CRED_RED+" Connecting to atem mini"+CEND)
    print("Remember to launch the other script for automatic switching with sound detection")

    switcher.connect(atem_mini_ip)
    switcher.waitForConnection()
    print(current_time()+CRED_RED+" Connected to atem mini"+CEND)
connection_to_switcher()


### Android stuff for ronin
if ronin:
    client = AdbClient(host="127.0.0.1", port=5037) # Default is "127.0.0.1" and 5037
    devices = client.devices()

    if len(devices) == 0:
        print('No devices')
        quit()

    device = devices[0]
    print(f'Connected to {device}')

def ronin_point(n):
    if n == 1:
        #synth_front
        device.shell('input touchscreen tap 145 840')
    if n == 2:
        #piano_left
        device.shell('input touchscreen tap 256 840')
    if n == 3:
        #synth_right
        device.shell('input touchscreen tap 385 840')
    if n == 4 :
        #battery
        device.shell('input touchscreen tap 474 840')
    if n == 5:
        #bass
        device.shell('input touchscreen tap 592 840')
    if n == 6 :
        #sarah_speak
        device.shell('input touchscreen tap 692 840')
    if n == 7:
        device.shell('input touchscreen tap 826 840')
    if n == 8:
        device.shell('input touchscreen tap 929 840')

    time.sleep(2)
    switcher.setCameraControlAutoFocus(3)
def camera(n,switcher): #Switches the camera
    '''
    :param n: the camera number
    :param switcher: the switcher
    :return: Changes the cameras
    '''
    try:
        switcher.setPreviewInputVideoSource(0, n)
        switcher.execAutoME(0)
    except:
        print(CRED_RED+"Error in camera()"+CEND)
def rotate_camera(list_of_cameras,switcher,position_ronin,last_cam):

    '''
    :param list_of_cameras: The cameras that will be used for the rotation
    :param switcher: the atem mini switcher
    :return: Selects camera input at random, time_sleep is how much time it takes to switch cameras
    '''

    n = random.choice(list_of_cameras)

    if n == g_angle:
        if ronin:
            c = random.choice(position_ronin)
            ronin_point(c)

    camera(n,switcher)

    if n == zoom:
        return str(n)+' - Zoom'
    if n == g_angle:
        if ronin:
            return str(n)+' - Grand angle - variation ronin '+str(c)
        else:
            return str(n)+' - Grand Angle'

    if n == camera_face:
        return str(n)+' - Camera Face'
    else:
        return str(n)+ ' Error ?'
def drum_level():
    '''
    :return: reads the file drum_status.txt created by Instrument_Level.py
    '''
    try:
        with open("drum_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(current_time()+"Error in drum_level, returning 0")
        return 0
def piano_level():
    '''
    :return: reads the file piano_status.txt created by Instrument_Level.py
    '''
    try:
        with open("piano_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(current_time()+"Error in piano_level, returning 0")
        return 0
def voice_level():
    '''
    :return: reads the file piano_status.txt created by Instrument_Level.py
    '''
    try:
        with open("voice_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(current_time()+"Error in voice_level, returning 0")
        return 0
def instrument_group_level():
    '''
    :return: reads the file instrument_status.txt created by Instrument_Level.py
    '''
    try:
        with open("instrument_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(current_time()+CRED_RED+" Error in instrument_group_level, returning 0"+CEND)
        return 0

# OSC client for sending messages to Ableton
client = udp_client.SimpleUDPClient("127.0.0.1", 11000)
# Create a dispatcher
disp = dispatcher.Dispatcher()

# Register a function to handle OSC messages on address "/live/device/get/parameters/value"
def volume_handler(*args):
    # print("Volume of track "+str(args[-3])) #found empiricaly

    if n == 1:
        with open("voice_status.txt", "w") as file:
            file.write(str(args[-3]))
            #print('Voix\t: ' + str(float(args[-3])))

    elif n == 3:
        with open("piano_status.txt", "w") as file:
            file.write(str(args[-3]))
            #print('Piano\t: ' + str(float(args[-3])))
    elif n == 2:
        with open("instrument_status.txt", "w") as file:
            file.write(str(args[-3]))
            #print('instru\t: ' + str(float(args[-3])))

    elif n == 4:
        with open("drum_status.txt", "w") as file:
            file.write(str(args[-3]))
            #print('Drums\t: ' + str(float(args[-3])))

disp.map("/live/device/get/parameters/value", volume_handler)
# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)
# Start the OSC server
server_thread = threading.Thread(target=server.serve_forever).start()

def main_values():
    global n
    n =1
    while True:
        # Request the parameters' values of the device, alternate between all instruments and just piano
        if n == 3:
            client.send_message("/live/device/get/parameters/value", [3, 2])
            time.sleep(0.2)
            n = 2

        elif n == 2:
            client.send_message("/live/device/get/parameters/value", [2, 1])
            time.sleep(0.2)
            n = 1
        elif n == 1:
            client.send_message("/live/device/get/parameters/value", [1, 2])
            time.sleep(0.2)
            n = 4
        elif n == 4:
            client.send_message("/live/device/get/parameters/value", [4, 1])
            time.sleep(0.2)
            n = 3
def camera_brain():
    while True:
        time.sleep(0.5)
        # If there's audio in the instruments group, then rotate cameras
        if instrument_group_level() > 0.005:

            if piano_level() > 0.0005:

                if voice_level() < 0.001:
                    print('No Voice')
                    camera_package = [zoom,zoom, g_angle,g_angle,g_angle, camera_face]

                elif voice_level() < 0.3:
                    print('Voice is low at '+str(voice_level())[0:5])
                    camera_package = [zoom,zoom,zoom, g_angle,g_angle,g_angle, camera_face]

                elif voice_level() > 0.6:
                    print('Voice is Loud at '+str(voice_level())[0:5]+' - switching to face camera mostly')
                    camera_package = [camera_face,camera_face,camera_face,camera_face,camera_face,camera_face,camera_face,camera_face,zoom,g_angle]

                else:
                    print('Voice moderate at '+str(voice_level())[0:5]+' - Switching to main mix')
                    camera_package = [zoom,  g_angle, camera_face]

                if drum_level() > 0.7:

                    print('Drum is loud '+str(drum_level())[0:5]+' - Switching to drum mix')
                    camera_package = [zoom, g_angle,g_angle, camera_face, camera_drums,camera_drums,camera_drums]


                print(current_time()+CRED_BLUE_2+' '+CEND+" Instruments Playing - With Piano - Rotating Cameras "+str(camera_package)+" -"+CRED_GREEN_2+" Current Camera: " +rotate_camera(camera_package,switcher,[1,2,6],last_cam)+CEND)

                for k in range(0, sleep_time):
                    time.sleep(1)
                    if piano_level() < 0.0005:
                        print(current_time()+CRED_BLUE_2+' '+CEND+CRED_BLUE+" Piano Stopped !"+CEND)
                        break

            else:

                # If there's audio in the instruments group,and no piano

                camera_package = [g_angle]

                if drum_level() > 0.7:
                    print('Drums are loud ' + str(drum_level())[0:5] + ' - Switching to drum mix')
                    camera_package = [g_angle,g_angle, camera_face, camera_drums,camera_drums,camera_drums]



                print(current_time()+CRED_GREEN+' '+CEND+" Instruments Playing - No Piano - Rotating Cameras - "+str(camera_package)+" - "+CRED_GREEN_2+'Current Camera: '+rotate_camera(camera_package,switcher,[2,6],last_cam)+CEND)

                for k in range(0, sleep_time):
                    time.sleep(1)
                    if instrument_group_level() < 0.0005:
                        print(current_time()+CRED_BLUE_2+' '+CEND+CRED_BLUE+" Instruments Off !"+CEND)
                        break
                    elif piano_level() > 0.0005:
                        print(current_time()+CRED_BLUE_2+' '+CEND+ CRED_BLUE+" Piano just came in !"+CEND)
                        break

        else:
            # If there's audio in the voice channel only

            camera_package = [camera_face,camera_face,camera_face,camera_face,camera_face,camera_face, camera_face,camera_face, camera_face, camera_face, g_angle]

            print(current_time()+CRED_ORANGE+' '+CEND+" Instruments Off - Rotating Cameras - "+str(camera_package)+'Current Camera: '+rotate_camera(camera_package,switcher,[2,6],last_cam))
            time.sleep(3)

main_values_thread = threading.Thread(target=main_values).start()
camera_brain_thread = threading.Thread(target=camera_brain).start()

