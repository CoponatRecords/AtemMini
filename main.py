# Automatic Scene Switcher for atem mini

import time
import PyATEMMax
import random
switcher = PyATEMMax.ATEMMax()

# Connect
atem_mini_ip = "192.168.0.123"

print("Connecting")
switcher.connect(atem_mini_ip)
switcher.waitForConnection()
print("Connected")

def camera(n): #Switches the camera
    return switcher.setProgramInputVideoSource(0, n)

def rotate_camera(list_of_cameras, time_sleep): #Selects camera input at random
    n = random.choice(list_of_cameras)
    camera(n)
    print("Current Camera:  "+str(n))
    time.sleep(time_sleep)


while True:
    rotate_camera([1,2,3], 2)