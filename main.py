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
    global number_of_tracks
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
    slider_files = []
    secondary_slider_files = []
    slider_names = []
    slider_box_files = []

    for k in range(number_of_tracks):
        slider_files.append(f"Track_{k}_status.txt")
        secondary_slider_files.append(f"Secondary_Track_{k}_status.txt")
        slider_names.append(f"Track {k}")
        slider_box_files.append(f"slider_{k}_box.txt")

    for file_path in slider_files + secondary_slider_files + slider_box_files:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as file:
                file.write('0000')  # Creating an empty file

    # Initialize checkbox states from files
    checkbox_states = [read_checkbox_states(i) for i in range(len(slider_files))]
    check_vars = [[None] * 4 for _ in range(len(slider_files))]

    # Add camera buttons
    for i, label in enumerate(cam_labels):
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
    for i, (slider_file, secondary_slider_file, slider_name) in enumerate(zip(slider_files, secondary_slider_files, slider_names)):
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

#Time to wait before trying to switch cameras
sleep_time = 10


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
    switcher.connect(atem_mini_ip)
    switcher.waitForConnection()
    print(current_time()+CRED_RED+" Connected to atem mini"+CEND)

connection_to_switcher()


def is_camera_active(camera_number):
    try:
        with open('active_camera.txt', 'r') as file:
            active_cameras = [int(line.strip()) for line in file]
            file.close()

        return active_cameras[camera_number - 1] == 1
    except (FileNotFoundError, IndexError, ValueError):
        return False

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

    with open('active_camera.txt', 'r') as file:
        active_cameras = [int(line.strip()) for line in file]
    print('active cameras '+ str(active_cameras))

    count=0
    for k in active_cameras:
        count = count + 1
        if k == 0 :
            while count in list_of_cameras:
                list_of_cameras.remove(count)

    print("list of cameras"+str(list_of_cameras))
    try:
        n = random.choice(list_of_cameras)
        print('Chosen camera is ' + str(n))

        write_digit_to_file(int(n))
        return int(n)

    except:
        print("No cameras available - default to  camera 1")
        return 1






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

def percentage(list):

    perc_1 = 100*list.count(1)/len(list)
    perc_2 = 100*list.count(2)/len(list)
    perc_3 = 100*list.count(3)/len(list)
    perc_4 = 100*list.count(4)/len(list)

    string = str(perc_1)[0:2]+'% Camera1 | '+'%'+str(perc_2)[0:2]+' Face | '+str(perc_3)[0:2]+'% Grand Angle |'+str(perc_4)[0:2]+'% Drums --- '
    return string

# Register a function to handle OSC messages on address "/live/device/get/parameters/value"
def osc_handler(*args):


    if args[0] == '/live/song/get/num_tracks':

        print('Number of tracks - '+str(args[1]))
        global number_of_tracks
        number_of_tracks =  int(args[1])

    elif args[0] == '/live/song/get/track_names':

        print('track_names - '+str(args))


    elif args[0] == '/live/track/get/output_meter_level':
        
        n = args[-2]
        with open("Track_"+str(n)+"_status.txt", "w") as file:
            file.write(str(args[-1]))
            file.close()

    else:
        print(args[0])


def ableton_track_level():
    global number_of_tracks
    while True:
        t = 0.1
        # Request the audio output value of the tracks

        for k in range(0, number_of_tracks):
            client.send_message("/live/track/get/output_meter_level",k)


        time.sleep(t)

def camera_brain():

    print("Brain Started")
    global number_of_tracks

    while True:

        if read_input_from_file('automated.txt') == True:

            slider_files = []
            secondary_slider_files = []
            slider_names = []
            slider_box_files = []

            for k in range(0, number_of_tracks):
                slider_files.append("Track_" + str(k) + "_status.txt")
                secondary_slider_files.append("Secondary_Track_" + str(k) + "_status.txt")
                slider_names.append("Track " + str(k))
                slider_box_files.append("slider_"+str(k)+"_box.txt")

            for file_path in slider_files + secondary_slider_files + slider_box_files:
                if not os.path.exists(file_path):
                    # Create the file if it doesn't exist
                    with open(file_path, 'w') as file:
                        file.write('0000')  # Creating an empty file

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
                    except :
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


import live
import random

global number_of_tracks
number_of_tracks = 0
# OSC client for sending messages to Ableton
client = udp_client.SimpleUDPClient("127.0.0.1", 11000)

# Create a dispatcher
disp = dispatcher.Dispatcher()
# Create a OSC server
server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 11001), disp)

# Start the OSC server
server_thread = threading.Thread(target=server.serve_forever).start()
disp.map("/live/track/get/output_meter_level", osc_handler)

client.send_message("/live/song/get/num_tracks", 99)
disp.map("/live/song/get/num_tracks", osc_handler)

disp.map("/live/song/get/track_data", osc_handler)



camera_brain_thread = threading.Thread(target=camera_brain).start()
gui_thread = threading.Thread(target=gui).start()
main_values_thread = threading.Thread(target=ableton_track_level()).start()



