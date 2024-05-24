'''
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

To run this script : right-click on this text, then click:  "Run 'main'"

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

This script reads the track_1.txt file and track_2.txt to switch cameras
The ATEM mini has to be on and connected through ethernet. Check the connection status with the "Atem Setup" app.
The ATEM mini's IP adress has to be set to 192.168.0.124

Ableton needs to have AbletonOSC installed : https://github.com/ideoforms/AbletonOSC

This script writes track_1.txt, track_2.txt.... with a value repres-
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
import time
import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
from PIL import Image, ImageTk
import PyATEMMax
import random
import threading
import time
import os
from plyer import notification
import numpy as np


start = time.time()

def write_digit_to_file(digit, filename='input.txt'):
    # Ensure the input is a valid digit (1, 2, 3, or 4)
    if digit not in [1, 2, 3, 4]:
        raise ValueError("Input must be one of the following digits: 1, 2, 3, or 4")

    # Write the digit to the file
    with open(filename, 'w') as file:
        file.write(str(digit))
        file.close()

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

switcher = PyATEMMax.ATEMMax()


class Switcher:
    def __init__(self, name):
        self.name = name

    def setPreviewInputVideoSource(self, source, number):
        print(f"Setting camera {number} to source {source}")

    def execAutoME(self, number):
        print(f"Executing Auto ME for camera {number}")
def highlight_button(buttons, selected_index, active_cameras):
    for idx, btn in enumerate(buttons):
        if active_cameras[idx] == 1:
            btn.configure(style='TButton')
    if 0 <= selected_index < len(buttons) and active_cameras[selected_index] == 1:
        buttons[selected_index].configure(style='Red.TButton')

def update_input_file(filename, value):
    try:
        with open(filename, 'w') as file:
            file.write(str(value))
            file.close()
    except Exception as e:
        print(f"Error updating input file: {e}")

def read_input_from_file(filename):
    try:
        with open(filename, 'r') as file:
            return float(file.read().strip())
        file.close()


    except (FileNotFoundError, ValueError):
        return None

def update_highlight(buttons, filename, active_cameras):
    input_value = read_input_from_file(filename)
    if input_value is not None:
        highlight_button(buttons, int(input_value) - 1, active_cameras)
    root.after(1000, update_highlight, buttons, filename, active_cameras)  # Check the file every 1000 milliseconds (1 second)

def toggle_automated(filename):
    try:
        # Read the current value from the file
        with open(filename, 'r') as file:
            value = int(file.read().strip())
            file.close()

    except FileNotFoundError:
        # If the file doesn't exist, create it with the initial value 0
        with open(filename, 'w') as file:
            file.write('0')
            file.close()

        print("Created automated.txt with initial value 0")
        return

    # Toggle the value
    new_value = 0 if value == 1 else 1

    # Write the new value back to the file
    with open(filename, 'w') as file:
        file.write(str(new_value))
        file.close()

    print(f"Automated toggle: {value} -> {new_value}")

    # Change button appearance based on the new value
    if new_value == 1:
        start_stop_btn.config(image=pause_icon, text="Stop AutoSwitch")
    else:
        start_stop_btn.config(image=start_icon, text="Start AutoSwitch")

def resize_image(image_path, width, height):
    original_image = Image.open(image_path)
    resized_image = original_image.resize((width, height), Image.LANCZOS)
    return ImageTk.PhotoImage(resized_image)

def save_active_cameras(active_cameras):
    with open('active_camera.txt', 'w') as f:
        for state in active_cameras:
            f.write(f"{state}\n")
    f.close()

def load_active_cameras():
    try:
        with open('active_camera.txt', 'r') as f:
            return [int(line.strip()) for line in f]
    except FileNotFoundError:
        return [1, 1, 1, 1]  # Default to all cameras active

def toggle_camera(idx, buttons, active_cameras):
    active_cameras[idx] = 0 if active_cameras[idx] == 1 else 1
    save_active_cameras(active_cameras)
    update_camera_button_style(idx, buttons, active_cameras)

def update_camera_button_style(idx, buttons, active_cameras):
    if active_cameras[idx] == 1:
        buttons[idx].configure(state=tk.NORMAL, style='TButton', command=lambda idx=idx: camera(idx + 1, switcher))
    else:
        buttons[idx].configure(state=tk.DISABLED, style='Grey.TButton')

def camera(n, switcher):
    try:
        switcher.setPreviewInputVideoSource(0, n)
        switcher.execAutoME(0)
        print(f"Camera {n} selected")
    except Exception as e:
        print(f"Error in camera(): {e}")

def read_value_from_file(filename):
    try:
        with open(filename, 'r') as file:
            value = float(file.read().strip())
            return value
    except (FileNotFoundError, ValueError):
        # Handle file not found or invalid content
        return 0.5

def update_sliders(sliders, filenames):
    for slider, filename in zip(sliders, filenames):
        value = read_value_from_file(filename)
        slider.set(value)
    root.after(1000, update_sliders, sliders, filenames)



def update_slider_file(slider, filename):
    value = slider.get()
    update_input_file(filename, value)

# Function to set the initial value of the slider from the text file
def set_slider_from_file(slider, filename):
    value = read_value_from_file(filename)
    if value is None:
        value = 0.5
        update_input_file(filename, value)
    slider.set(value)

def create_checkboxes(root, row, column, count):
    checkboxes = []
    for i in range(count):
        checkbox = tk.IntVar()
        chkbox = tk.Checkbutton(root, variable=checkbox)
        chkbox.grid(row=row, column=column + i, padx=5)
        checkboxes.append(checkbox)
    return checkboxes

def update_checkbox_file(filename, checkboxes):
    checkbox_values = [str(checkbox.get()) for checkbox in checkboxes]
    with open(filename, 'w') as file:
        file.write(','.join(checkbox_values))
        file.close()


def set_checkboxes_from_file(filename, checkboxes):
    with open(filename, 'r') as file:
        values = file.read().split(',')
        for value, checkbox in zip(values, checkboxes):
            checkbox.set(int(value))
        file.close()


def update_slider_file(slider, file):
    with open(file, 'w') as f:
        f.write(str(slider.get()))

        f.close()


# Function to update the checkbox file when a checkbox is clicked
def checkbox_clicked(slider_idx, box_idx):
    checkbox_states[slider_idx][box_idx] = check_vars[slider_idx][box_idx].get()
    state_str = ''.join(str(state) for state in checkbox_states[slider_idx])
    with open(f"slider_{slider_idx}_box.txt", 'w') as file:
        file.write(state_str)
        file.close()


# Function to create a slider with a subslider
def create_slider_with_subslider(frame, main_slider_file, sub_slider_file):

    main_slider = ttk.Scale(frame, from_=0.0, to=1.0, orient="horizontal")
    sub_slider = ttk.Scale(frame, from_=0.0, to=1.0, orient="horizontal", style = "Custom.Horizontal.TScale")

    main_slider.pack(fill='x')
    sub_slider.pack(fill='x')

    main_slider.bind("<ButtonRelease>", lambda event, s=main_slider, f=main_slider_file: update_slider_file(s, f))
    sub_slider.bind("<ButtonRelease>", lambda event, s=sub_slider, f=sub_slider_file: update_slider_file(s, f))


    return main_slider, sub_slider

# Function to read checkbox states from a file
def read_checkbox_states(slider_idx):
    file_path = f"slider_{slider_idx}_box.txt"
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            state_str = file.read().strip()
            file.close()

            return [int(char) for char in state_str]
    else:
        return [0, 0, 0, 0]  # Default state if file doesn't exist

def gui():
    global root, start_stop_btn, start_icon, pause_icon
    global check_vars, checkbox_states

    root = ThemedTk(theme="arc")
    root.title("Camera Bot")
    root.attributes('-topmost', True)  # Make the window always on top

    style = ttk.Style()
    style.configure('TButton', font=('Helvetica', 12), padding=10, foreground="#333", background="#fff", relief="flat")
    style.configure('Red.TButton', font=('Helvetica', 12, 'bold'), background='darkred', foreground='red')
    style.configure('Grey.TButton', font=('Helvetica', 12), padding=10, background='grey', foreground='darkgrey')
    style.map('Red.TButton', background=[('!active', 'red'), ('active', 'darkred')])

    cam_labels = ["Cam 1", "Cam 2", "Cam 3", "Cam 4"]
    active_cameras = load_active_cameras()

    buttons = []
    checkbuttons = []
    sliders = []
    secondary_sliders = []
    slider_files = ["Track_0_status.txt", "Track_1_status.txt", "Track_2_status.txt", "Track_3_status.txt", "Track_4_status.txt",
                    "Track_5_status.txt", "Track_6_status.txt", "Track_7_status.txt"]
    secondary_slider_files = ["Secondary_Track_0_status.txt", "Secondary_Track_1_status.txt", "Secondary_Track_2_status.txt", "Secondary_Track_3_status.txt",
                              "Secondary_Track_4_status.txt", "Secondary_Track_5_status.txt", "Secondary_Track_6_status.txt", "Secondary_Track_7_status.txt"]
    slider_names = ["Track 0", "Track 1", "Track 2", "Track 3", "Track 4", "Track 5",
                    "Track 6", "Track 7"]

    # Initialize checkbox states from files
    checkbox_states = [read_checkbox_states(i) for i in range(len(slider_files))]
    check_vars = [[None] * 4 for _ in range(len(slider_files))]

    # Add camera buttons
    for i, label in enumerate(cam_labels, start=0):
        btn = ttk.Button(root, text=label)
        btn.grid(row=0, column=i, padx=10, pady=10)
        buttons.append(btn)

        check_var = tk.IntVar(value=active_cameras[i])
        chk = tk.Checkbutton(root, variable=check_var,
                             command=lambda idx=i: toggle_camera(idx, buttons, active_cameras))
        chk.grid(row=1, column=i)
        checkbuttons.append(chk)

        update_camera_button_style(i, buttons, active_cameras)

    # Add sliders and secondary sliders in a column under camera buttons
    for i, (slider_file, secondary_slider_file, slider_name) in enumerate(zip(slider_files, secondary_slider_files, slider_names), start=0):
        name_label = ttk.Label(root, text=slider_name)
        name_label.grid(row=i * 3 + 3, column=0, padx=10, sticky='w')

        for j in range(4):
            check_var = tk.IntVar(value=checkbox_states[i][j])
            chkbox = tk.Checkbutton(root, variable=check_var, command=lambda slider_idx=i, box_idx=j: checkbox_clicked(slider_idx, box_idx))
            chkbox.grid(row=i * 3 + 4, column=j)
            check_vars[i][j] = check_var

        # Primary slider
        slider_frame = ttk.Frame(root)
        slider_frame.grid(row=i * 3 + 3, column=1, columnspan=3, padx=10, pady=10, sticky='we')
        main_slider, sub_slider = create_slider_with_subslider(slider_frame, slider_file, secondary_slider_file)
        sliders.append(main_slider)

        # Secondary slider
        secondary_slider_frame = ttk.Frame(root)
        secondary_slider_frame.grid(row=i * 3 + 4, column=1, columnspan=3, padx=10, pady=10, sticky='we')
        secondary_sliders.append(sub_slider)

    switcher = Switcher("my_switcher")

    # Load icons for start and pause buttons
    start_icon = resize_image("start_icon.png", 24, 24)
    pause_icon = resize_image("stop_icon.png", 24, 24)

    # Create start/stop button with icon and text
    start_stop_btn = ttk.Button(root, image=pause_icon, text="Stop AutoSwitch", compound=tk.LEFT,
                                command=lambda: toggle_automated('automated.txt'))
    start_stop_btn.grid(row=len(slider_files) * 3 + 3, column=0, columnspan=len(cam_labels), pady=10)

    # Start the periodic updates
    update_highlight(buttons, 'input.txt', active_cameras)
    update_sliders(sliders, slider_files)
    update_sliders(secondary_sliders, secondary_slider_files)

    text1 = "Pas de mouvement avec le Son ?"
    text2 = "Ableton - Option - Préférences - Link/Tempo/MIDI - Enlever et remettre AbletonOSC ."

    label = tk.Label(root, text=text1, font=("Helvetica", 8, "italic"))
    label.grid(row=30, column=0, columnspan=4, sticky="ew")
    label = tk.Label(root, text=text2, font=("Helvetica", 8, "italic"))
    label.grid(row=31, column=0, columnspan=4, sticky="ew")

    label = tk.Label(root, text='COPONAT RECORDS 2024', font=("Helvetica", 5, "bold"))
    label.grid(row=33, column=0, columnspan=4, sticky="ew")
    root.mainloop()

update_input_file('automated.txt',1)

#used to add color in terminal
CRED_RED = '\033[91m'
CRED_GREEN = '\033[42m'
CRED_BLUE= '\033[34m'
CRED_BLUE_2= '\033[44m'
CRED_GREEN_2 = '\033[92m'
CRED_ORANGE = '\033[43m'
CEND= '\033[0m'

#Entrées Atem mini:

Camera1 = 1
Camera4 = 4
Camera2 = 2
Camera3 = 3


#starting cam
notification = False

# Ableton Track Settings
# The number is the position of the track, starting count at 0 for the first one
Track_0 = 0
Track_1 = 1
Track_2 = 2
Track_3 = 3
Track_4 = 4
Track_5 = 5
Track_6 = 6
Track_7 = 7

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
def is_camera_active(camera_number):
    try:
        with open('active_camera.txt', 'r') as file:
            active_cameras = [int(line.strip()) for line in file]
            file.close()

        return active_cameras[camera_number - 1] == 1
    except (FileNotFoundError, IndexError, ValueError):
        return False
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
        #Track_6
        device.shell('input touchscreen tap 327 949')
        print("Ronin on " + str(n))

    elif n == 3:
        #Track_4
        device.shell('input touchscreen tap 465 949')
        print("Ronin on " + str(n))

    elif n == 4 :
        #Track_5
        device.shell('input touchscreen tap 583 949')
        print("Ronin on " + str(n))

    elif n == 5:
        #Track_3
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

    switcher.setCameraControlAutoFocus(Camera1)
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
        update_input_file('input.txt', n)
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
                message = 'Camera 1'
            elif n == 2:
                message = 'Camera 2'
            elif n == 3:
                message = 'Grand 3'
            elif n == 4:
                message = 'Camera 4'

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

def filter_active_cameras(data_list):
    # Read active camera statuses from the file
    try:
        with open('active_camera.txt', 'r') as file:
            active_cameras = [int(line.strip()) for line in file]
    except FileNotFoundError:
        print("active_camera.txt not found.")
        return data_list
    except ValueError:
        print("Error reading active_camera.txt. Ensure it contains only integers.")
        return data_list

    # Filter the data list based on the active cameras
    filtered_list = []

    for index, data in enumerate(data_list):
        if index < len(active_cameras) and active_cameras[index] == 1:
            filtered_list.append(data)

    return filtered_list
def rotate_camera(list_of_cameras,switcher):

    '''
    :param list_of_cameras: The cameras that will be used for the rotation
    :param switcher: the atem mini switcher
    :return: Selects camera input at random, time_sleep is how much time it takes to switch cameras
    '''

    print(list_of_cameras)
    with open('active_camera.txt', 'r') as file:
        active_cameras = [int(line.strip()) for line in file]
    print('active cameras '+ str(active_cameras))

    count=0
    for k in active_cameras:
        count = count + 1
        if k == 0 :
            while count in list_of_cameras:
                list_of_cameras.remove(count)
            print(count)

    print(list_of_cameras)
    n = random.choice(list_of_cameras)

    print('Chosen camera is '+str(n))
    write_digit_to_file(int(n))
    return int(n)


def Track_level(id):

    '''
    :return: reads the file Track_id_status.txt created by Instrument_Level.py
    '''
    try:
        with open("Track_"+str(id)+"_status.txt", "r") as file:
            content = file.read()
            file.close()

            return float(content)
    except Exception:
        print(current_time()+"Error in track "+str(id)+", returning 0")
        return 0

def Track_7_level():
    '''
    :return: reads the file Track_7_status.txt created by Instrument_Level.py
    '''
    try:
        with open("Track_7_status.txt", "r") as file:
            content = file.read()
            file.close()

            return float(content)
    except Exception:
        print(current_time()+"Error in drum_level, returning 0")
        return 0
def Track_5_level():
    '''
    :return: reads the file drum_status.txt created by Instrument_Level.py
    '''
    try:
        with open("Track_5_status.txt", "r") as file:
            content = file.read()
            file.close()

            return float(content)
    except:
        print(current_time()+"Error in Track_5_level, returning 0")
        return 0
def Track_4_level():
    '''
    :return: reads the file Track_4_status.txt created by Instrument_Level.py
    '''
    try:
        with open("Track_4_status.txt", "r") as file:
            content = file.read()
            file.close()

            return float(content)
    except:
        print(current_time()+"Error in Track_4_level, returning 0")
        return 0
def Track_3_level():
    '''
    :return: reads the file drum_status.txt created by Instrument_Level.py
    '''
    try:
        with open("Track_3_status.txt", "r") as file:
            content = file.read()
            file.close()

            return float(content)
    except:
        print(current_time()+"Error in Track_3_level, returning 0")
        return 0
def Track_2_level():
    '''
    :return: reads the file track_2.txt created by Instrument_Level.py
    '''
    try:
        with open("Track_2_status.txt", "r") as file:
            content = file.read()
            file.close()

            return float(content)
    except:
        print(current_time()+"Error in Track_2_level, returning 0")
        return 0
def Track_0_level():
    '''
    :return: reads the file track_0.txt created by Instrument_Level.py
    '''
    try:
        with open("track_0_status.txt", "r") as file:
            content = file.read()
            file.close()

            return float(content)
    except:
        print(current_time()+"Error in Track_0_level, returning 0")
        return 0
def Track_6_level():
    '''
    :return: reads the file Track_6_status.txt created by Instrument_Level.py
    '''
    try:
        with open("Track_6_status.txt", "r") as file:
            content = file.read()
            file.close()

            return float(content)
    except:
        print(current_time()+"Error in Track_6_level, returning 0")
        return 0
def Track_1_level():
    '''
    :return: reads the file track_1.txt created by Instrument_Level.py
    '''
    try:
        with open("Track_1_status.txt", "r") as file:
            content = file.read()
            file.close()

            return float(content)
    except Exception as e:
        print(current_time()+CRED_RED+" Error in Track_1_level(), returning 0"+CEND+str(e))
        return 0

def percentage(list):

    perc_1 = 100*list.count(1)/len(list)
    perc_2 = 100*list.count(2)/len(list)
    perc_3 = 100*list.count(3)/len(list)
    perc_4 = 100*list.count(4)/len(list)

    string = str(perc_1)[0:2]+'% Camera1 | '+'%'+str(perc_2)[0:2]+' Face | '+str(perc_3)[0:2]+'% Grand Angle |'+str(perc_4)[0:2]+'% Drums --- '
    return string

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

        if Track_2_level() > .0002:
            position_list.append(1)
            position_list_txt.append('Track_2')
            if debug:
                print('Track_2')
        if Track_6_level() > .02:
            position_list.append(2)
            position_list_txt.append('Track_6')
            if debug:
                print('Track_6')
        if Track_4_level() > .005:
            position_list.append(3)
            position_list_txt.append('Track_4')
            if debug:
                print('Track_4')
        if Track_5_level() > .05:
            position_list.append(4)
            position_list_txt.append('Track_5')
            if debug:
                print('Track_5')
        if Track_3_level() > .05:
            position_list.append(5)
            position_list_txt.append('Track_3')
            if debug:
                print('Track_3')
        if Track_7_level() > .05:
            position_list.append(6)
            position_list_txt.append('Track_7_level')
            if debug:
                print('drum_level')
        if Track_0_level() > .04:
            position_list.append(6)
            position_list_txt.append('Track_0_level')
            if debug:
                print('Track_0_level')

        if Track_0_level() > .7: #Only Voice
            position_list = [6]
            position_list_txt = ['Track_0_level']
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

# Register a function to handle OSC messages on address "/live/device/get/parameters/value"
def volume_handler(*args):
    n = args[-2]

    with open("Track_"+str(n)+"_status.txt", "w") as file:
        file.write(str(args[-1]))
        file.close()


# OSC client for sending messages to Ableton
client = udp_client.SimpleUDPClient("127.0.0.1", 11000)
# Create a dispatcher
disp = dispatcher.Dispatcher()
# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)
# Start the OSC server
server_thread = threading.Thread(target=server.serve_forever).start()
disp.map("/live/track/get/output_meter_level", volume_handler)

def ableton_track_level():
    while True:
        t = 0.1
        # Request the audio output value of the tracks
        client.send_message("/live/track/get/output_meter_level",Track_0)
        client.send_message("/live/track/get/output_meter_level",Track_1)
        client.send_message("/live/track/get/output_meter_level",Track_2)
        client.send_message("/live/track/get/output_meter_level",Track_3)
        client.send_message("/live/track/get/output_meter_level",Track_4)
        client.send_message("/live/track/get/output_meter_level",Track_5)
        client.send_message("/live/track/get/output_meter_level",Track_6)
        client.send_message("/live/track/get/output_meter_level",Track_7)


        time.sleep(t)

def new_camera_brain():

    while True:

        if read_input_from_file('automated.txt') == True:


            slider_files = ["Track_0_status.txt", "Track_1_status.txt", "Track_2_status.txt", "Track_3_status.txt",
                            "Track_4_status.txt",
                            "Track_5_status.txt", "Track_6_status.txt", "Track_7_status.txt"]
            secondary_slider_files = ["Secondary_Track_0_status.txt", "Secondary_Track_1_status.txt",
                                      "Secondary_Track_2_status.txt", "Secondary_Track_3_status.txt",
                                      "Secondary_Track_4_status.txt", "Secondary_Track_5_status.txt",
                                      "Secondary_Track_6_status.txt", "Secondary_Track_7_status.txt"]
            slider_box_files = ["slider_0_box.txt", "slider_1_box.txt", "slider_2_box.txt", "slider_3_box.txt",
                            "slider_4_box.txt",
                            "slider_5_box.txt", "slider_6_box.txt", "slider_7_box.txt"]

            sound_levels = []  # Initialize a list to store the sound levels

            # Iterate over each file path in the list
            for file_path in slider_files:
                # Open the file in read mode
                with open(file_path, 'r') as file:

                    # Read the first line of the file and convert it to a float
                    first_line = file.readline().strip()
                    try :
                        sound_level = float(first_line)
                    except:
                        sound_level = 0
                    sound_levels.append(sound_level)  # Append the sound level to the list

            slider_levels = []  # Initialize a list to store the sound levels

            # Iterate over each file path in the list
            for file_path in secondary_slider_files:
                attempt = 1
                while attempt <= 3:  # Retry up to 3 times
                    try:
                        # Open the file in read mode
                        with open(file_path, 'r') as file:
                            # Read the first line of the file and convert it to a float
                            first_line = file.readline().strip()
                            slider_level = float(first_line)
                            slider_levels.append(slider_level)  # Append the slider level to the list
                        break  # Break out of the retry loop if successful
                    except FileNotFoundError:
                        print(f"File '{file_path}' not found. Retry attempt {attempt}/3.")
                        attempt += 1
                        time.sleep(0.1)  # Wait for 1 second before retrying

            slider_boxes = []  # Initialize a list to store the sound levels

            # Iterate over each file path in the list
            for file_path in slider_box_files:
                # Open the file in read mode
                with open(file_path, 'r') as file:
                    # Read the first line of the file and convert it to a float
                    first_line = file.readline().strip()
                    slider_box = float(first_line)
                    slider_boxes.append(slider_box)  # Append the sound level to the list


            k = 0
            camera_mix = 0
            for sound in range(len(slider_files)) :
                sound    =  sound_levels[k]
                slider    = slider_levels[k]
                box_value = int(slider_boxes[k])

                if slider < sound:
                    camera_mix = camera_mix + box_value

                k = k+1
            cam1 = int(camera_mix/1000)
            cam2 = int((camera_mix-cam1*1000)/100)
            cam3 =int((camera_mix-cam1*1000 - cam2*100)/10)
            cam4 = camera_mix - cam1*1000 - cam2*100 - cam3*10

            cams = [cam1, cam2, cam3, cam4]

            cam_list = []
            for i in range(len(cams)):
                for j in range(cams[i]):
                    cam_list.append(i+1)

            if not len(cam_list) == 0:
                print('camera mix ' + str(cam_list))
                camera(int(rotate_camera(cam_list, switcher)),switcher)

            else:
                print('AutoSwitch is not changing any cameras at the moment')

        time.sleep(5)

main_values_thread = threading.Thread(target=ableton_track_level).start()
gui_thread = threading.Thread(target=gui).start()
camera_brain_thread = threading.Thread(target=new_camera_brain).start()

if ronin == True:

    ronin_thread = threading.Thread(target=auto_ronin).start()
    print("Ronin bot is on")
