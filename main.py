'''
Automatic Scene Switcher for Atem Mini

ToDo :

    add  gui
    regroup both scripts on one start button
'''

import time
import PyATEMMax
import random

def piano_status():
    with open("piano_status.txt", "r") as file:
        content = file.read()
        a = float(content)
    return a


def track_status():
    with open("instrument_status.txt", "r") as file:
        content = file.read()
        a = float(content)
    return a

def connection_to_switcher():
    switcher = PyATEMMax.ATEMMax()

    # Connect
    atem_mini_ip = "192.168.0.123"

    print("Connecting to atem mini")
    print("Remember to launch the other script for automatic switching with sound detection")

    switcher.connect(atem_mini_ip)
    switcher.waitForConnection()
    print("Connected to atem mini")
switcher = PyATEMMax.ATEMMax()
connection_to_switcher()

def camera(n): #Switches the camera
    return switcher.setProgramInputVideoSource(0, n)

def rotate_camera(list_of_cameras): #Selects camera input at random, time_sleep is how much time it takes to switch cameras
    n = random.choice(list_of_cameras)
    camera(n)
    return str(("Current Camera:  "+str(n)))



while True:
    if track_status() > 0.005: #If there's audio in the instruments group, then rotate cameras

        if piano_status() > 0.005:
            print("Instruments Playing - With Piano - Rotating Cameras 123- " + rotate_camera([1,2,3]))
        else:
            print("Instruments Playing - No Piano - Rotating Cameras - 23" + rotate_camera([1,2,3]))

        time.sleep(8)


    else:
        print("Instruments Off - Camera on Face")
        camera(2)



