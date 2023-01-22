# This is a sample Python script.

# Press Maj+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import time
import PyATEMMax
import random
switcher = PyATEMMax.ATEMMax()

# Connect
print("Connection en cours")
switcher.connect("192.168.0.123")
switcher.waitForConnection()
print("Connected")
def camera(n):
    return switcher.setProgramInputVideoSource(0, n)

def rotate_camera(list_of_cameras, time_sleep):
    n = random.choice(list_of_cameras)
    camera(n)
    print("Current Camera:  "+str(n))
    time.sleep(time_sleep)


while True:
    rotate_camera([1,2,3], 2)