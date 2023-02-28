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

This script writes instrument_status.txt, piano_status.txt.... with a value repres-
enting the current audio level of the tracks.


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

# Ableton Track Settings
# The number is the position of the track, starting count at 0 for the first one
Voix = 1
Group_instrument = 2
Piano = 3
Drums = 4
Bass = 14
Prophet = 15
Vibra = 16
Omnisphere = 18

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

    try:
        with open("last_ronin.txt", "r") as file:
            content = file.read()

    except Exception as e:
        print('Moving on')

    if str(n) == content:
        pass

    elif n == 1:
        #piano
        device.shell('input touchscreen tap 174 949')
        print("Ronin on " + str(n))

    elif n == 2:
        #omnisphere
        device.shell('input touchscreen tap 327 949')
        print("Ronin on " + str(n))

    elif n == 3:
        #prophet
        device.shell('input touchscreen tap 465 949')
        print("Ronin on " + str(n))

    elif n == 4 :
        #vibra
        device.shell('input touchscreen tap 583 949')
        print("Ronin on " + str(n))

    elif n == 5:
        #bass
        device.shell('input touchscreen tap 737 949')
        print("Ronin on " + str(n))

    elif n == 6 :
        #batterie
        device.shell('input touchscreen tap 873 949')
        print("Ronin on " + str(n))

    try:
        with open("last_ronin.txt", "w") as file:
            file.write(str(n))
    except:
        print("Error in last_ronin.txt")
        return 0

    switcher.setCameraControlAutoFocus(zoom)
def ronin_startup():
    for k in range(0,5):
        ronin_point(k)
        time.sleep(5)
def camera(n,switcher): #Switches the camera

    '''
    :param n: the camera number
    :param switcher: the switcher
    :return: Changes the cameras
    '''
    try:
        switcher.setPreviewInputVideoSource(0, n)
        switcher.execAutoME(0)
        time.sleep(0.5)

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

    camera(n,switcher)

    if n == zoom:
        return str(n) + ' - Zoom'


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
    except Exception:
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
def auto_ronin():
    debug = False
    k = 0
    while True:
        try:
            with open("last_ronin.txt", "r") as file:
                content = file.read()
        except Exception as e:
            print('Moving on')

        time.sleep(8)

        position_list = []
        position_list_txt = []

        if piano_level() > .0002:
            position_list.append(1)
            position_list_txt.append('piano')
            if debug:
                print('piano')
        if omnisphere_level() > .02:
            position_list.append(2)
            position_list_txt.append('omnisphere')
            if debug:
                print('omnisphere')
        if prophet_level() > .005:
            position_list.append(3)
            position_list_txt.append('prophet')
            if debug:
                print('prophet')
        if vibra_level() > .05:
            position_list.append(4)
            position_list_txt.append('vibra')
            if debug:
                print('vibra')
        if bass_level() > .05:
            position_list.append(5)
            position_list_txt.append('bass')
            if debug:
                print('bass')
        if drum_level() > .05:
            position_list.append(6)
            position_list_txt.append('drum_level')
            if debug:
                print('drum_level')
        if voice_level() > .04:
            position_list.append(6)
            position_list_txt.append('voice_level')
            if debug:
                print('voice_level')

        if voice_level() > .7: #Only Voice
            position_list = [6]
            position_list_txt = ['voice_level']
            if debug:
                print('voice only')

        position_list = 10*position_list


        try:
            if 3 in position_list or 4 in position_list:
                for k in range(len(position_list)):
                    try:
                        position_list.remove(6)
                    except:
                        pass
        except:
            pass

        try:

            if int(content) in position_list:
                if k < 5:
                    if debug:
                        print('k' + str(k))
                        print('content: ' + str(content))
                        print('position_list: ' + str(position_list))

                    k = k + 1
                    time.sleep(1)
                    pass
                else:
                    if debug:
                        print('k' + str(k))
                        print('content: ' + str(content))
                        print('position_list: ' + str(position_list))
                    k = 0
                    point = random.choice(range(len(position_list)))
                    ronin_point(position_list[point])

            else:
                k = 0
                if debug:
                    print('k' + str(k))
                    print('content: ' + str(content))
                    print('position_list: ' + str(position_list))
                point = random.choice(range(len(position_list)))
                ronin_point(position_list[point])

        except Exception as e :
            print(e)
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
    n = args[-2]
    if n == Voix:
        with open("voice_status.txt", "w") as file:
            file.write(str(args[-1]))
            #print('Voix\t: ' + str(args))
    elif n == Group_instrument:
        with open("instrument_status.txt", "w") as file:
            file.write(str(args[-1]))
            #print('instru\t: ' + str(args))
    elif n == Piano:
        with open("piano_status.txt", "w") as file:
            file.write(str(args[-1]))
            #print('Piano\t: ' + str(args))
    elif n == Drums:
        with open("drum_status.txt", "w") as file:
            file.write(str(args[-1]))
            #print('Drums\t: ' + str(args))
    elif n == Bass:
        with open("bass_status.txt", "w") as file:
            file.write(str(args[-1]))
            # print('bass\t: ' + str(args))
    elif n == Prophet:
        with open("prophet_status.txt", "w") as file:
            file.write(str(args[-1]))
            #print('prophet\t: ' + str(args))
    elif n == Vibra:
        with open("vibra_status.txt", "w") as file:
            file.write(str(args[-1]))
            #print('vibra\t: ' + str(args))
    elif n == Omnisphere:
        with open("omnisphere_status.txt", "w") as file:
                file.write(str(args[-1]))
                #print('omnisphere\t: ' + str(args))
    else:
        pass

disp.map("/live/track/get/output_meter_level", volume_handler)

# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)
# Start the OSC server
server_thread = threading.Thread(target=server.serve_forever).start()

def ableton_track_level():
    while True:
        t = 0.1
        # Request the audio output value of the tracks
        client.send_message("/live/track/get/output_meter_level",Piano)
        client.send_message("/live/track/get/output_meter_level",Group_instrument)
        client.send_message("/live/track/get/output_meter_level",Voix)
        client.send_message("/live/track/get/output_meter_level",Drums)
        client.send_message("/live/track/get/output_meter_level",Bass)
        client.send_message("/live/track/get/output_meter_level",Prophet)
        client.send_message("/live/track/get/output_meter_level",Vibra)
        client.send_message("/live/track/get/output_meter_level",Omnisphere)

        time.sleep(t)
def camera_brain():
    while True:
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

                print(current_time()+CRED_BLUE_2+' '+CEND+" Instruments Playing - With Piano - "+percentage(camera_package)+" -"+CRED_GREEN_2+" Camera: " +rotate_camera(camera_package,switcher)+CEND)

                for k in range(0, sleep_time):
                    time.sleep(1)
                    if piano_level() < 0.00005:
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

                print(current_time()+CRED_GREEN+' '+CEND+" Instruments Playing - No Piano - "+percentage(camera_package)+" - "+CRED_GREEN_2+'Camera: '+rotate_camera(camera_package,switcher)+CEND)

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
            if ronin:
                camera_package.append(zoom)
                ronin_point(6)
            print(current_time()+CRED_ORANGE+' '+CEND+" Instruments Off - "+percentage(camera_package)+'Camera: '+rotate_camera(camera_package,switcher))
            time.sleep(3)

main_values_thread = threading.Thread(target=ableton_track_level).start()
camera_brain_thread = threading.Thread(target=camera_brain).start()

if ronin == True:
    ronin_thread = threading.Thread(target=auto_ronin).start()
    print("Ronin bot is on")
