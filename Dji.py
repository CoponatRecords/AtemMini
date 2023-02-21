

#just testing stuff here

import time
from ppadb.client import Client as AdbClient

'''

setCameraControlFocus(camera:ATEMConstant, focus:int) -> None
 Args:
        camera: see ATEMCameras
        focus (int): 0-65535
        
        
setCameraControlVideomode(camera:ATEMConstant, fps:int, resolution:int, interlaced:int)
setCameraControlWhiteBalance


'''

client = AdbClient(host="127.0.0.1", port=5037) # Default is "127.0.0.1" and 5037
devices = client.devices()

if len(devices) == 0:
    print('No devices')
    quit()

device = devices[0]

print(f'Connected to {device}')

device.shell('input touchscreen tap 370 1150')
time.sleep(1)

device.shell('input tap 27')