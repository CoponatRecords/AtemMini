'''
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

To run this script : right-click on this text, then click:  "Run 'main'"

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

This script reads the instrument_status.txt file and piano_status.txt to switch cameras
The ATEM mini has to be on and connected through ethernet. Check the connection status with the "Atem Setup" app.
The ATEM mini's IP adress has to be set to 192.168.0.124

Ableton needs to have AbletonOSC installed : https://github.com/ideoforms/AbletonOSC

This script writes instrument_status.txt, piano_status.txt, drum_status.txt, voice_status.txt files with a value repres-
enting the current audio level of the tracks.

This works with an envelope follower (Max4Live) linked to a utility's gain on the third (group all instrument) and four-
th (piano with a vst) tracks of ableton

We us threading to run the processes in parallel.


If using the ronin :

Start the dji app and go  into the 'create' then 'pursuit' tab
Write .\adb start-server in the terminal window and press enter
Then launch this script

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
'''
from ppadb.client import Client as AdbClient
from pythonosc import dispatcher, osc_server, udp_client

import PyATEMMax
import random
import threading
import time
import os
from plyer import notification


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
notification = False

#Time to wait before trying to switch cameras
sleep_time = 10

#if ronin not connected: put ronin = False (no gimbal)
ronin = False
if not ronin:
    print("No Ronin in the script")
def current_time():
    '''
    :return: time in hh:mm:ss format
    '''
    t = time.localtime()
    return str(time.strftime("%H:%M:%S", t)+' ')

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
        #piano
        device.shell('input touchscreen tap 174 949')
    if n == 2:
        #omnisphere
        device.shell('input touchscreen tap 327 949')
    if n == 3:
        #prophet
        device.shell('input touchscreen tap 465 949')
    if n == 4 :
        #vibra
        device.shell('input touchscreen tap 583 949')
    if n == 5:
        #bass
        device.shell('input touchscreen tap 737 949')
    if n == 6 :
        #batterie
        device.shell('input touchscreen tap 873 949')

    try:
        with open("last_ronin.txt", "w") as file:
            file.write(str(n))
    except:
        print("Error in last_ronin.txt")
        return 0

    switcher.setCameraControlAutoFocus(zoom)
    time.sleep(2.5)

def camera(n,switcher): #Switches the camera

    '''
    :param n: the camera number
    :param switcher: the switcher
    :return: Changes the cameras
    '''
    try:
        switcher.setPreviewInputVideoSource(0, n)
        switcher.execAutoME(0)

        try:
            with open("last_cam.txt", "r") as file:
                last_cam = file.read()
        except:
            try:
                with open("last_cam.txt", "w") as file:
                    file.write(str(n))
            except:
                print("Error in reseting last_cam.txt")
                return 0

        if last_cam != str(n) and (notification == True):

            if n == 1:
                message = 'Zoom'
            elif n == 2:
                message = 'Camera Face'
            elif n == 3:
                message = 'Grand Angle'
            elif n == 4:
                message = 'Camera Drums'

            notification.notify(
                title='Camera',
                message=message,
                app_icon=None,
                timeout=1,
            )

            try:
                with open("last_cam.txt", "w") as file:
                    file.write(str(n))
            except:
                print("Error in file writing of last_cam")
                return 0


    except:
        print(CRED_RED+"Error in camera()"+CEND)
def rotate_camera(list_of_cameras,switcher):

    '''
    :param list_of_cameras: The cameras that will be used for the rotation
    :param switcher: the atem mini switcher
    :return: Selects camera input at random, time_sleep is how much time it takes to switch cameras
    '''

    n = random.choice(list_of_cameras)

    if n == zoom:
        if ronin:
            positions_possible, position_list_txt = position_ronin()
            c = random.choice(positions_possible)

            ronin_point(c)

    camera(n,switcher)

    if n == zoom:
        if ronin:
            if c == 1:
                t = 'Piano'
            if c == 2:
                t = 'Omnisphere'
            if c == 3:
                t = 'Prophet'
            if c == 4:
                t = 'Vibra'
            if c == 5:
                t = 'Bass'
            if c == 6:
                t = 'Drums'
            return str(n) + ' - Zoom - ' + t +" - "+ str(position_list_txt)
        else:
            return str(n) + ' -Zoom'

    if n == g_angle:
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
def vibra_level():
    '''
    :return: reads the file drum_status.txt created by Instrument_Level.py
    '''
    try:
        with open("vibra_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(current_time()+"Error in drum_level, returning 0")
        return 0
def prophet_level():
    '''
    :return: reads the file prophet_status.txt created by Instrument_Level.py
    '''
    try:
        with open("prophet_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(current_time()+"Error in prophet_level, returning 0")
        return 0
def bass_level():
    '''
    :return: reads the file drum_status.txt created by Instrument_Level.py
    '''
    try:
        with open("bass_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(current_time()+"Error in bass_level, returning 0")
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
    :return: reads the file voice_status.txt created by Instrument_Level.py
    '''
    try:
        with open("voice_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(current_time()+"Error in voice_level, returning 0")
        return 0
def omnisphere_level():
    '''
    :return: reads the file omnisphere_status.txt created by Instrument_Level.py
    '''
    try:
        with open("omnisphere_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(current_time()+"Error in omnisphere_level, returning 0")
        return 0

def position_ronin():

    position_list = []
    position_list_txt = []
    if piano_level() > .5:
        position_list.append(1)
        position_list_txt.append('piano')
    if omnisphere_level() > .2:
        position_list.append(2)
        position_list_txt.append('omnisphere')
    if prophet_level() > .5:
        position_list.append(3)
        position_list_txt.append('prophet')
    if vibra_level() > .5:
        position_list.append(4)
        position_list_txt.append('vibra')
    if bass_level() > .5:
        position_list.append(5)
        position_list_txt.append('bass')
    if drum_level() > .5:
        position_list.append(6)
        position_list_txt.append('drum')

    if position_list == []:
        position_list = [1]
        position_list_txt= ['piano']


    return [position_list, position_list_txt]

def percentage(list):


    perc_1 = 100*list.count(1)/len(list)
    perc_2 = 100*list.count(2)/len(list)
    perc_3 = 100*list.count(3)/len(list)
    perc_4 = 100*list.count(4)/len(list)

    string = str(perc_1)[0:2]+'% Zoom | '+'%'+str(perc_2)[0:2]+' Face | '+str(perc_3)[0:2]+'% Grand Angle |'+str(perc_4)[0:2]+'% Drums --- '
    return string
def instrument_group_level():
    '''
    :return: reads the file instrument_status.txt created by Instrument_Level.py
    '''
    try:
        with open("instrument_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except Exception as e:
        print(current_time()+CRED_RED+" Error in instrument_group_level, returning 0"+CEND+str(e))
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
    elif n == 5:
        with open("bass_status.txt", "w") as file:
            file.write(str(args[-3]))
            #print('bass\t: ' + str(float(args[-3])))
    elif n == 6:
        with open("prophet_status.txt", "w") as file:
            file.write(str(args[-3]))
            #print('prophet\t: ' + str(float(args[-3])))
    elif n == 7:
        with open("vibra_status.txt", "w") as file:
            file.write(str(args[-3]))
            #print('vibra\t: ' + str(float(args[-3])))
    elif n == 8:
        with open("omnisphere_status.txt", "w") as file:
                file.write(str(args[12]))
                #print('omnisphere\t: ' + str(float(args[12])))

disp.map("/live/device/get/parameters/value", volume_handler)
#disp.map("/live/track/get/output_meter_level", volume_handler)

# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)
# Start the OSC server
server_thread = threading.Thread(target=server.serve_forever).start()

def main_values():
    global n
    n = 1
    while True:
        # Request the parameters' values of the device, alternate between all instruments and just piano
        if n == 3:
            client.send_message("/live/device/get/parameters/value", [3, 2]) #piano
            #client.send_message("/live/track/start_listen/output_meter_level", 3)

            time.sleep(0.1)
            n = 2

        elif n == 2:
            client.send_message("/live/device/get/parameters/value", [2, 1]) #isntrument group
            time.sleep(0.1)
            n = 1
        elif n == 1:
            client.send_message("/live/device/get/parameters/value", [1, 2]) #Voix
            time.sleep(0.1)
            n = 4
        elif n == 4:
            client.send_message("/live/device/get/parameters/value", [4, 1]) #drum
            time.sleep(0.1)
            n = 5
        elif n == 5:
            client.send_message("/live/device/get/parameters/value", [14, 2]) #Bass
            time.sleep(0.1)
            n = 6
        elif n == 6:
            client.send_message("/live/device/get/parameters/value", [15, 2]) #prophet
            time.sleep(0.1)
            n = 7
        elif n == 7:
            client.send_message("/live/device/get/parameters/value", [16, 2]) #vibra
            time.sleep(0.1)
            n = 8

        elif n == 8:
            client.send_message("/live/device/get/parameters/value", [18, 2]) #omnisphere
            time.sleep(0.1)
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

                if ronin:
                    camera_package.append(zoom)
                    camera_package.append(zoom)

                print(current_time()+CRED_BLUE_2+' '+CEND+" Instruments Playing - With Piano - "+percentage(camera_package)+" -"+CRED_GREEN_2+" Current Camera: " +rotate_camera(camera_package,switcher)+CEND)

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
                    camera_package = [g_angle,g_angle, camera_face,camera_drums,camera_drums]

                if ronin:
                    camera_package.append(zoom)
                    camera_package.append(zoom)




                print(current_time()+CRED_GREEN+' '+CEND+" Instruments Playing - No Piano - "+percentage(camera_package)+" - "+CRED_GREEN_2+'Current Camera: '+rotate_camera(camera_package,switcher)+CEND)

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

            print(current_time()+CRED_ORANGE+' '+CEND+" Instruments Off - "+percentage(camera_package)+'Current Camera: '+rotate_camera(camera_package,switcher))
            time.sleep(3)

main_values_thread = threading.Thread(target=main_values).start()
camera_brain_thread = threading.Thread(target=camera_brain).start()
