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


import time
import PyATEMMax
import random

#used to add color in terminal
CRED_RED = '\033[91m'
CRED_GREEN = '\033[42m'
CRED_BLUE= '\033[34m'
CRED_BLUE_2= '\033[44m'
CRED_GREEN_2 = '\033[92m'
CRED_ORANGE = '\033[43m'
CEND= '\033[0m'

#used as global variable to print less stuff in the terminal
camera_face = 1

#time to wait before trying to switch cameras
sleep_time = 8


#Functions to communicate with the Atem Mini
def connection_to_switcher():
    # Connect
    atem_mini_ip = "192.168.0.124"

    print(CRED_RED+"Connecting to atem mini"+CEND)
    print("Remember to launch the other script for automatic switching with sound detection")

    switcher.connect(atem_mini_ip)
    switcher.waitForConnection()
    print(CRED_RED+"Connected to atem mini"+CEND)

def camera(n,switcher): #Switches the camera
    try:
        switcher.setProgramInputVideoSource(0, n)
    except:
        print(CRED_RED+"Error in camera()"+CEND)

def rotate_camera(list_of_cameras,switcher): #Selects camera input at random, time_sleep is how much time it takes to switch cameras
    n = random.choice(list_of_cameras)
    camera(n,switcher)
    return str(n)

switcher = PyATEMMax.ATEMMax()
connection_to_switcher()

#Functions to read the files created by Instrument_Level.py
def piano_level():
    try:
        with open("piano_status.txt", "r") as file:
            content = file.read()
            return float(content)

    except:
        print("Error in piano_level, returning 0")
        return 0

def instrument_group_level():
    try:
        with open("instrument_status.txt", "r") as file:
            content = file.read()
            return float(content)
    except:
        print(CRED_RED+"Error in instrument_group_level, returning 0"+CEND)
        return 0

while True:
    if instrument_group_level() > 0.005: #If there's audio in the instruments group, then rotate cameras
        camera_face = 1

        if piano_level() > 0.005:
            print(CRED_BLUE_2+' '+CEND+" Instruments Playing - With Piano - Rotating Cameras 123 -"+CRED_GREEN_2+" Current Camera: " +rotate_camera([1,2,3],switcher)+CEND)

            for k in range(0, sleep_time):
                time.sleep(1)
                if piano_level() < 0.005:
                    print(CRED_BLUE_2+' '+CEND+CRED_BLUE+" Piano Stopped !"+CEND)
                    break

        else:
            print(CRED_GREEN+' '+CEND+" Instruments Playing - No Piano - Rotating Cameras - 23 - "+CRED_GREEN_2+'Current Camera: '+rotate_camera([2,3],switcher)+CEND)

            for k in range(0, sleep_time):
                time.sleep(1)
                if instrument_group_level() < 0.005:
                    print(CRED_BLUE_2+' '+CEND+CRED_BLUE+" Instruments Off !"+CEND)
                    break
                elif piano_level() > 0.005:
                    print(CRED_BLUE_2+' '+CEND+ CRED_BLUE+" Piano just came in !"+CEND)
                    break

    else:
        if camera_face == 1:
            print(CRED_ORANGE+' '+CEND+" Instruments Off - Camera on Face - Camera 2")
            camera_face = 0

        camera(2,switcher)
        time.sleep(1)