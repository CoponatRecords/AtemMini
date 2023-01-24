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

import PySimpleGUI as sg

import time
import PyATEMMax
import random
switcher = PyATEMMax.ATEMMax()

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
        print("Error in instrument_group_level, returning 0")
        return 0


def connection_to_switcher():
    # Connect
    atem_mini_ip = "192.168.0.124"

    print("Connecting to atem mini")
    print("Remember to launch the other script for automatic switching with sound detection")

    switcher.connect(atem_mini_ip)
    switcher.waitForConnection()
    print("Connected to atem mini")

connection_to_switcher()

def camera(n,switcher): #Switches the camera
    try:
        switcher.setProgramInputVideoSource(0, n)
    except:
        print("Error in camera()")
    return

def rotate_camera(list_of_cameras,switcher): #Selects camera input at random, time_sleep is how much time it takes to switch cameras
    n = random.choice(list_of_cameras)
    camera(n,switcher)
    return str(("Current Camera:  "+str(n)))

while True:

    sleep_time = 8
    if instrument_group_level() > 0.005: #If there's audio in the instruments group, then rotate cameras

        if piano_level() > 0.005:
            print("Instruments Playing - With Piano - Rotating Cameras 123 - " + rotate_camera([1,2,3],switcher))

            for k in range(0, sleep_time):
                time.sleep(1)
                if piano_level() < 0.005:
                    print("Piano Stopped !")
                    break

        else:
            print("Instruments Playing - No Piano - Rotating Cameras - 23 -" + rotate_camera([2,3],switcher))

            for k in range(0, sleep_time):
                time.sleep(1)
                if instrument_group_level() < 0.005:
                    print("Instruments Off !")
                    break
                elif piano_level() > 0.005:
                    print("Piano just came in !")
                    break

    else:
        print("Instruments Off - Camera on Face - Camera 2")
        camera(2,switcher)
        time.sleep(1)



