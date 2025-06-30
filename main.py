import asyncio
import platform
import socket
import threading
import time
import os
import random
import signal
import subprocess
import re
from pythonosc import dispatcher, osc_server, udp_client
import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
from PIL import Image, ImageTk, ImageDraw

# PyATEMMax and plyer are external dependencies, assuming they are installed.
try:
    import PyATEMMax
except ImportError:
    print("PyATEMMax not found. Running in dummy switcher mode.")
    class PyATEMMax: # Dummy class if not installed
        class ATEMMax:
            def __init__(self): pass
            def connect(self, ip): print(f"Dummy ATEM connecting to {ip}")
            def waitForConnection(self): time.sleep(0.1)
            def disconnect(self): print("Dummy ATEM disconnected")
            def setPreviewInputVideoSource(self, program, source): pass
            def execAutoME(self, mix_effect_block): pass
    PyATEMMax = PyATEMMax

try:
    from plyer import notification
except ImportError:
    print("Plyer not found. Notifications will be disabled.")
    class NotificationDummy:
        def notify(self, **kwargs): pass
    notification = NotificationDummy()
    enable_notification = False

# Global variables
start = time.time()
number_of_tracks = 0
switcher = PyATEMMax.ATEMMax()
server = None

current_sound_levels = {}
current_threshold_levels = {}
current_checkbox_states = {}
data_lock = threading.Lock()

root = None
sliders = []
secondary_sliders = []
start_stop_btn = None
start_icon = None
pause_icon = None
check_vars = []
checkbox_states = []


# ANSI color codes for terminal (for console output, not GUI)
CRED_RED = '\033[91m'
CRED_GREEN = '\033[42m'
CRED_BLUE = '\033[34m'
CRED_BLUE_2 = '\033[44m'
CRED_GREEN_2 = '\033[92m'
CRED_ORANGE = '\033[43m'
CEND = '\033[0m'

# ATEM Mini camera inputs
Camera1 = 1
Camera2 = 2
Camera3 = 3
Camera4 = 4

# Settings
sleep_time = 10

# --- Helper Functions ---
def write_digit_to_file(digit, filename='input.txt'):
    if digit not in [1, 2, 3, 4]:
        raise ValueError("Input must be one of the following digits: 1, 2, 3, or 4")
    with open(filename, 'w') as file:
        file.write(str(digit))

def update_input_file(filename, value):
    try:
        with open(filename, 'w') as file:
            file.write(str(value))
    except Exception as e:
        print(f"Error updating input file '{filename}': {e}")

def read_input_from_file(filename):
    try:
        with open(filename, 'r') as file:
            return float(file.read().strip())
    except (FileNotFoundError, ValueError):
        return None

def read_value_from_file(filename):
    try:
        with open(filename, 'r') as file:
            value = float(file.read().strip())
            return value
    except (FileNotFoundError, ValueError):
        return 0.5

def current_time():
    t = time.localtime()
    return str(time.strftime("%H:%M:%S", t) + ' ')

def resize_image(image_path, width, height):
    try:
        original_image = Image.open(image_path)
        resized_image = original_image.resize((width, height), Image.LANCZOS)
        return ImageTk.PhotoImage(resized_image)
    except FileNotFoundError:
        print(f"Warning: Image file not found at {image_path}. Creating a placeholder.")
        img = Image.new('RGB', (width, height), color = 'gray')
        d = ImageDraw.Draw(img)
        d.text((width//4, height//4), "IMG", fill=(0,0,0))
        return ImageTk.PhotoImage(img)


def save_active_cameras(active_cameras):
    with open('active_camera.txt', 'w') as f:
        for state in active_cameras:
            f.write(f"{state}\n")

def load_active_cameras():
    try:
        with open('active_camera.txt', 'r') as f:
            return [int(line.strip()) for line in f]
    except FileNotFoundError:
        return [1, 1, 1, 1]

def read_checkbox_states(slider_idx):
    file_path = f"slider_{slider_idx}_box.txt"
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            state_str = file.read().strip()
            state_str = state_str.ljust(4, '0')
            return [int(char) for char in state_str[:4]]
    else:
        with open(file_path, 'w') as file:
            file.write('0000')
        return [0, 0, 0, 0]

# --- ATEM Mini Control (using PyATEMMax) ---
def connection_to_switcher():
    global switcher
    atem_mini_ip = "192.168.0.240"
    print(current_time() + CRED_RED + " Connecting to ATEM Mini..." + CEND)
    try:
        switcher.connect(atem_mini_ip)
        switcher.waitForConnection()
        print(current_time() + CRED_RED + " Connected to ATEM Mini" + CEND)
    except Exception as e:
        print(current_time() + CRED_RED + f" Failed to connect to ATEM Mini: {e}" + CEND)
        switcher = PyATEMMax.ATEMMax("Dummy_Switcher")

def disconnect_switcher():
    global switcher
    if isinstance(switcher, PyATEMMax.ATEMMax):
        try:
            switcher.disconnect()
            print(current_time() + CRED_RED + " Disconnected from ATEM Mini" + CEND)
        except Exception as e:
            print(current_time() + CRED_RED + f" Error disconnecting from ATEM Mini: {e}" + CEND)

def camera(n, switcher_instance):
    try:
        switcher_instance.setPreviewInputVideoSource(0, n)
        switcher_instance.execAutoME(0)
        print(f"Camera {n} selected")
        update_input_file('input.txt', n)

        try:
            with open("last_cam.txt", "r") as file:
                last_cam = file.read().strip()
        except FileNotFoundError:
            last_cam = None

        if last_cam != str(n) :
            messages = {1: 'Camera 1', 2: 'Camera 2', 3: 'Grand 3', 4: 'Camera 4'}

        try:
            with open("last_cam.txt", "w") as file:
                file.write(str(n))
        except Exception as e:
            print(f"Error in file writing of last_cam: {e}")
    except Exception as e:
        print(f"Error in camera(): {e}")

# --- OSC Server and Client Setup ---
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True

def kill_port_process(port):
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(
                ["netstat", "-aon"], capture_output=True, text=True, shell=True
            )
            output = result.stdout
            pid = None
            for line in output.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = re.split(r'\s+', line.strip())
                    pid = parts[-1]
                    break
            if pid:
                print(current_time() + CRED_RED + f" Found process with PID {pid} using port {port}" + CEND)
                try:
                    subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, text=True, check=True)
                    print(current_time() + CRED_RED + f" Killed process with PID {pid}" + CEND)
                    time.sleep(1)
                    return True
                except subprocess.CalledProcessError as e:
                    print(current_time() + CRED_RED + f" Failed to kill process with PID {pid}: {e}" + CEND)
                    return False
            else:
                print(current_time() + CRED_RED + f" No process found using port {port}" + CEND)
                return True
        else:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"], capture_output=True, text=True
            )
            output = result.stdout.strip()
            if output:
                lines = output.splitlines()
                for line in lines[1:]:
                    parts = line.split()
                    pid = parts[1]
                    print(current_time() + CRED_RED + f" Found process with PID {pid} using port {port}" + CEND)
                    subprocess.run(["kill", "-9", pid], capture_output=True, text=True)
                    print(current_time() + CRED_RED + f" Killed process with PID {pid}" + CEND)
                    time.sleep(1)
                    return True
            else:
                print(current_time() + CRED_RED + f" No process found using port {port}" + CEND)
                return True
    except subprocess.CalledProcessError as e:
        print(current_time() + CRED_RED + f" Error executing command to kill process on port {port}: {e}" + CEND)
        return False
    except Exception as e:
        print(current_time() + CRED_RED + f" Unexpected error while killing process on port {port}: {e}" + CEND)
        return False

def cleanup(signum=None, frame=None):
    global server
    print(current_time() + CRED_RED + " Cleaning up resources..." + CEND)
    if server:
        try:
            server.shutdown()
            server.server_close()
            print(current_time() + CRED_RED + " OSC server shut down" + CEND)
        except Exception as e:
            print(current_time() + CRED_RED + f" Error shutting down OSC server: {e}" + CEND)
    disconnect_switcher()
    os._exit(0)

# --- OSC Callbacks ---
def osc_handler(*args):
    global number_of_tracks, sliders, root
    if args[0] == '/live/song/get/num_tracks':
        print(current_time() + 'Number of tracks - ' + str(args[1]))
        number_of_tracks = int(args[1])
    elif args[0] == '/live/track/get/output_meter_level':
        n = int(args[-2])
        level = float(args[-1])
        with data_lock:
            current_sound_levels[n] = level

        if root and sliders and n < len(sliders):
            root.after_idle(lambda: sliders[n].set_main(level))

# --- Core Logic Functions ---
def ableton_track_level():
    global number_of_tracks, client
    client.send_message("/live/song/get/num_tracks", 0)
    time.sleep(0.5)

    while True:
        if number_of_tracks > 0:
            for k in range(number_of_tracks):
                client.send_message("/live/track/get/output_meter_level", k)
        time.sleep(0.1)

def rotate_camera(list_of_cameras):
    try:
        n = random.choice(list_of_cameras)
        print(f'{current_time()} Chosen camera is {n}')
        write_digit_to_file(int(n))
        return int(n)
    except IndexError:
        print(f"{current_time()} No cameras available in the filtered list - defaulting to camera 2")
        return 2
    except Exception as e:
        print(f"{current_time()} Error in rotate_camera: {e}")
        return 2

def camera_brain():
    print(current_time() + "Brain Started")
    global number_of_tracks, current_sound_levels, current_threshold_levels, current_checkbox_states, switcher

    while True:
        if read_input_from_file('automated.txt') == 1:
            with data_lock:
                sound_levels = [current_sound_levels.get(k, 0.0) for k in range(number_of_tracks)]
                threshold_levels = [current_threshold_levels.get(k, 0.5) for k in range(number_of_tracks)]
                checkbox_states_copy = [current_checkbox_states.get(k, [0, 0, 0, 0]) for k in range(number_of_tracks)]

            camera_mix_counts = [0, 0, 0, 0]

            for k in range(len(sound_levels)):
                sound = sound_levels[k]
                threshold = threshold_levels[k]
                box_values = checkbox_states_copy[k]

                if threshold < sound:
                    for cam_idx in range(4):
                        if box_values[cam_idx] == 1:
                            camera_mix_counts[cam_idx] += 1

            cam_list = []
            for i in range(len(camera_mix_counts)):
                for _ in range(camera_mix_counts[i]):
                    cam_list.append(i + 1)

            try:
                with open('active_camera.txt', 'r') as file:
                    gui_active_cameras = [int(line.strip()) for line in file]
            except FileNotFoundError:
                gui_active_cameras = [1, 1, 1, 1]

            filtered_cam_list = [cam for cam in cam_list if cam-1 < len(gui_active_cameras) and gui_active_cameras[cam-1] == 1]

            if len(filtered_cam_list) > 0:
                print(f'{current_time()} Camera mix candidates: {filtered_cam_list}')
                camera(rotate_camera(filtered_cam_list), switcher)
            else:
                print(f'{current_time()} AutoSwitch is not changing any cameras at the moment (no sound above threshold or no active cameras chosen for tracks).')
        time.sleep(sleep_time)

# --- GUI Components and Logic ---
class CustomDualSlider:
    def __init__(self, parent, from_=0.0, to=1.0):
        self.from_ = from_
        self.to = to
        self.width = 400
        self.height = 20
        self.thumb_size = 10

        self.canvas = tk.Canvas(parent, width=self.width, height=self.height, highlightthickness=0, bg="#1a1a1a", bd=0)
        self.value_main = from_
        self.value_sub = from_

        self.track = self.canvas.create_rectangle(0, 9, self.width, 11, fill="#555555", outline="")

        # This is the threshold indicator, now a clear vertical line
        self.fill_sub = self.canvas.create_rectangle(0, 0, 0, self.height, fill="#777777", outline="")

        self.fill_main = self.canvas.create_rectangle(0, 8, 0, 12, fill="#007aff", outline="")

        # The thumb for the sub (threshold) slider - now visually present
        self.thumb_sub = self.canvas.create_oval(0, 2, self.thumb_size, 18, fill="white", outline="#999999")

        self.drag_indicator = None

        self.canvas.tag_bind(self.thumb_sub, "<Button-1>", self.start_drag_sub)
        self.canvas.tag_bind(self.thumb_sub, "<B1-Motion>", self.move_sub)
        self.canvas.tag_bind(self.thumb_sub, "<ButtonRelease-1>", self.release_sub)
        self.canvas.bind("<Button-1>", self.start_drag_sub_on_canvas)
        self.canvas.bind("<B1-Motion>", self.move_sub_on_canvas)
        self.canvas.bind("<ButtonRelease-1>", self.release_sub_on_canvas)

        self.command_main = None
        self.command_sub = None
        self.set_main(from_)
        self.set_sub(from_)

    def start_drag_sub(self, event):
        self.move_sub_value_from_event(event)
        if self.drag_indicator:
            self.canvas.delete(self.drag_indicator)
        x_pos = (self.value_sub - self.from_) / (self.to - self.from_) * (self.width - self.thumb_size) + self.thumb_size / 2
        self.drag_indicator = self.canvas.create_rectangle(x_pos - 1, 0, x_pos + 1, self.height, fill="#bbbbbb", outline="")

    def start_drag_sub_on_canvas(self, event):
        self.move_sub_value_from_event(event)
        if self.drag_indicator:
            self.canvas.delete(self.drag_indicator)
        x_pos = (self.value_sub - self.from_) / (self.to - self.from_) * (self.width - self.thumb_size) + self.thumb_size / 2
        self.drag_indicator = self.canvas.create_rectangle(x_pos - 1, 0, x_pos + 1, self.height, fill="#bbbbbb", outline="")

    def move_sub_value_from_event(self, event):
        x = max(0, min(self.width - self.thumb_size, event.x - self.thumb_size / 2))
        new_value = self.from_ + (x / (self.width - self.thumb_size)) * (self.to - self.from_)
        self.set_sub(new_value)

    def move_sub(self, event):
        self.move_sub_value_from_event(event)
        if self.drag_indicator:
            x_pos = (self.value_sub - self.from_) / (self.to - self.from_) * (self.width - self.thumb_size) + self.thumb_size / 2
            self.canvas.coords(self.drag_indicator, x_pos - 1, 0, x_pos + 1, self.height)

    def move_sub_on_canvas(self, event):
        if "button1" in str(event.state).lower():
            self.move_sub(event)

    def release_sub(self, event):
        self.release_sub_on_canvas(event)

    def release_sub_on_canvas(self, event):
        if self.command_sub:
            self.command_sub()
        if self.drag_indicator:
            self.canvas.delete(self.drag_indicator)
            self.drag_indicator = None

    def set_main(self, value):
        self.value_main = max(self.from_, min(self.to, float(value)))
        x = (self.value_main - self.from_) / (self.to - self.from_) * self.width
        self.canvas.coords(self.fill_main, 0, 8, x, 12)
        self.update_fill_color()
        if self.command_main:
            self.command_main()

    def set_sub(self, value):
        self.value_sub = max(self.from_, min(self.to, float(value)))
        x_thumb = (self.value_sub - self.from_) / (self.to - self.from_) * (self.width - self.thumb_size)
        self.canvas.coords(self.thumb_sub, x_thumb, 2, x_thumb + self.thumb_size, 18)
        self.canvas.coords(self.fill_sub, x_thumb + self.thumb_size / 2, 0, x_thumb + self.thumb_size / 2, self.height)
        self.update_fill_color()

    def update_fill_color(self):
        if self.value_main > self.value_sub:
            self.canvas.itemconfig(self.fill_main, fill="#34c759")
        else:
            self.canvas.itemconfig(self.fill_main, fill="#ff453a")

    def subget(self):
        return self.value_sub

    def get(self):
        return self.value_main

    def bind_main(self, command):
        self.command_main = command

    def bind_sub(self, command):
        self.command_sub = command

def create_slider_with_subslider(frame, main_slider_file, sub_slider_file):
    slider = CustomDualSlider(frame)
    slider.bind_sub(lambda: update_slider_file(slider, sub_slider_file, is_sub=True))
    return slider, slider

def update_slider_file(slider_instance, filename, is_sub=False):
    global current_threshold_levels
    value = slider_instance.subget()
    match = re.search(r'Track_(\d+)', filename)
    if match:
        track_idx = int(match.group(1))
        with data_lock:
            current_threshold_levels[track_idx] = value
    update_input_file(filename, value)

def update_highlight(buttons, filename, active_cameras):
    input_value = read_input_from_file(filename)
    if input_value is not None:
        highlight_button(buttons, int(input_value) - 1, active_cameras)
    if root:
        root.after(250, update_highlight, buttons, filename, active_cameras)

def update_sliders_from_files(sliders_list, filenames, is_sub=False):
    for slider, filename in zip(sliders_list, filenames):
        value = read_value_from_file(filename)
        if is_sub:
            slider.set_sub(value)
    if root:
        root.after(250, update_sliders_from_files, sliders_list, filenames, is_sub)

def toggle_automated(filename):
    global start_stop_btn, start_icon, pause_icon
    try:
        with open(filename, 'r') as file:
            value = int(file.read().strip())
    except FileNotFoundError:
        with open(filename, 'w') as file:
            file.write('0')
        value = 0
        print(f"{current_time()} Created automated.txt with initial value 0")

    new_value = 0 if value == 1 else 1
    with open(filename, 'w') as file:
        file.write(str(new_value))
    print(f"{current_time()} Automated toggle: {value} -> {new_value}")

    if start_stop_btn:
        if new_value == 1:
            start_stop_btn.config(image=pause_icon, text="")
        else:
            start_stop_btn.config(image=start_icon, text="")

def toggle_camera(idx, buttons, active_cameras):
    active_cameras[idx] = 0 if active_cameras[idx] == 1 else 1
    save_active_cameras(active_cameras)
    update_camera_button_style(idx, buttons, active_cameras)

def update_camera_button_style(idx, buttons, active_cameras):
    if active_cameras[idx] == 1:
        buttons[idx].configure(state=tk.NORMAL, style='Camera.TButton')
        buttons[idx].config(command=lambda idx=idx: camera(idx + 1, switcher))
    else:
        buttons[idx].configure(state=tk.DISABLED, style='Disabled.TButton')
        buttons[idx].config(command=None)

def checkbox_clicked(slider_idx, box_idx):
    global check_vars, checkbox_states, current_checkbox_states
    checkbox_states[slider_idx][box_idx] = check_vars[slider_idx][box_idx].get()
    state_str = ''.join(str(state) for state in checkbox_states[slider_idx])
    with data_lock:
        current_checkbox_states[slider_idx] = checkbox_states[slider_idx][:]
    with open(f"slider_{slider_idx}_box.txt", 'w') as file:
        file.write(state_str)

def highlight_button(buttons, selected_index, active_cameras):
    for idx, btn in enumerate(buttons):
        if active_cameras[idx] == 1:
            btn.configure(style='Camera.TButton')
    if 0 <= selected_index < len(buttons) and active_cameras[selected_index] == 1:
        buttons[selected_index].configure(style='Red.TButton')

# --- Main GUI Function ---
def gui():
    global number_of_tracks, root, start_stop_btn, start_icon, pause_icon, check_vars, checkbox_states, sliders, secondary_sliders

    root = ThemedTk(theme="arc")
    root.title("Aperture Control")
    root.attributes('-topmost', True)
    root.configure(bg="#1a1a1a")

    # --- Styling Configuration (Corrected) ---
    style = ttk.Style()
    style.theme_use("arc")

    app_font = ('Helvetica Neue', 10)
    title_font = ('Helvetica Neue', 12, 'bold')
    button_font = ('Helvetica Neue', 11)

    style.configure('.', font=app_font, background="#1a1a1a", foreground="#cccccc")
    style.map('.', background=[('disabled', '#333333')])

    # General Button Style (for Start/Stop button)
    style.configure('TButton',
                    font=button_font,
                    padding=[10, 5],
                    relief="flat",
                    focuscolor="#444444",
                    focusthickness=0,
                    bordercolor="#555555",
                    borderwidth=1)
    style.map('TButton',
              # Define colors for pressed, then active, then the default state.
              background=[('pressed', '#333333'), ('active', '#555555'), ('!disabled', '#444444')],
              foreground=[('!disabled', 'green')]) # White text for all non-disabled states.

    # Camera buttons (Normal/Active)
    style.configure('Camera.TButton', font=button_font, foreground="black")
    style.map('Camera.TButton',
              # Explicitly set the blue background for the normal (!disabled) state.
              background=[('pressed', '#005bb5'), ('active', '#34aadc'), ('!disabled', '#007aff')],
              foreground=[('!disabled', 'green')])

    # Highlighted (Selected) camera button
    style.configure('Red.TButton', font=button_font, foreground="red")
    style.map('Red.TButton',
              # Explicitly set the red background for the normal (!disabled) state.
              background=[('pressed', '#cc382e'), ('active', 'red'), ('!disabled', '#ff453a')],
              foreground=[('!disabled', 'red')])

    # Disabled camera buttons
    style.configure('Disabled.TButton', font=button_font, relief="flat")
    style.map('Disabled.TButton',
              background=[('disabled', '#555555')],
              foreground=[('disabled', '#aaaaaa')])

    # Label styles
    style.configure('TLabel', font=app_font, background="#1a1a1a", foreground="#cccccc")
    style.configure('Title.TLabel', font=title_font, background="#1a1a1a", foreground="#ffffff")

    # Checkbutton styles
    style.configure('TCheckbutton',
                    font=app_font,
                    background="black",
                    foreground="#cccccc",
                    indicatoron=False,
                    relief="flat",
                    padding=[5, 5])
    style.map('TCheckbutton',
              background=[('selected', 'grey'), ('!selected', 'grey'), ('active', 'grey')],
              foreground=[('selected', '#ffffff'), ('!selected', '#cccccc')])

    # --- GUI Layout ---
    cam_labels = ["Cam 1", "Cam 2", "Cam 3", "Cam 4"]
    active_cameras = load_active_cameras()

    # Frame for Camera Control Buttons
    camera_control_frame = ttk.Frame(root, padding="15 10", style='TFrame')
    camera_control_frame.pack(fill=tk.X, pady=(15, 5))

    buttons = []
    for i, label_text in enumerate(cam_labels):
        btn = ttk.Button(camera_control_frame, text=label_text, command=lambda idx=i: toggle_camera(idx, buttons, active_cameras))
        btn.grid(row=0, column=i, padx=5, pady=5, sticky='ew')
        buttons.append(btn)
        update_camera_button_style(i, buttons, active_cameras)

    for i in range(len(cam_labels)):
        camera_control_frame.grid_columnconfigure(i, weight=1)


    # Frame for Global Automation Toggle
    auto_control_frame = ttk.Frame(root, padding="15 10", style='TFrame')
    auto_control_frame.pack(fill=tk.X, pady=5)

    start_icon = resize_image("start_icon.png", 24, 24)
    pause_icon = resize_image("stop_icon.png", 24, 24)

    start_stop_btn = ttk.Button(auto_control_frame, image=pause_icon, text="", compound=tk.LEFT,
                                command=lambda: toggle_automated('automated.txt'), style='TButton')
    start_stop_btn.pack(pady=10, expand=True)

    if read_input_from_file('automated.txt') == 1:
        start_stop_btn.config(image=pause_icon, text="")
    else:
        start_stop_btn.config(image=start_icon, text="")

    # Frame for Sliders and Checkboxes
    sliders_checkboxes_frame = ttk.Frame(root, padding="15 10", style='TFrame')
    sliders_checkboxes_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    sliders.clear()
    secondary_sliders.clear()
    check_vars.clear()
    checkbox_states.clear()

    slider_files = []
    secondary_slider_files = []
    slider_names = []
    slider_box_files = []

    for k in range(number_of_tracks):
        slider_files.append(f"Track_{k}_status.txt")
        secondary_slider_files.append(f"Secondary_Track_{k}_status.txt")
        slider_names.append(f"Track {k}")
        slider_box_files.append(f"slider_{k}_box.txt")

    for k in range(number_of_tracks):
        sound_file = f"Track_{k}_status.txt"
        if not os.path.exists(sound_file):
            with open(sound_file, 'w') as file:
                file.write('0.0')
        with data_lock:
            current_sound_levels[k] = read_value_from_file(sound_file)

        threshold_file = f"Secondary_Track_{k}_status.txt"
        if not os.path.exists(threshold_file):
            with open(threshold_file, 'w') as file:
                file.write('0.5')
        with data_lock:
            current_threshold_levels[k] = read_value_from_file(threshold_file)

        box_file = f"slider_{k}_box.txt"
        if not os.path.exists(box_file):
            with open(box_file, 'w') as file:
                file.write('0000')
        with data_lock:
            current_checkbox_states[k] = read_checkbox_states(k)

    checkbox_states = [current_checkbox_states.get(i, [0,0,0,0]) for i in range(number_of_tracks)]
    check_vars = [[None] * 4 for _ in range(number_of_tracks)]


    for i, (slider_file, secondary_slider_file, slider_name) in enumerate(zip(slider_files, secondary_slider_files, slider_names)):
        track_row_frame = ttk.Frame(sliders_checkboxes_frame, padding="0 5", style='TFrame')
        track_row_frame.pack(fill=tk.X, expand=True, pady=5)

        name_label = ttk.Label(track_row_frame, text=slider_name, style='TLabel')
        name_label.grid(row=0, column=0, padx=(0,10), sticky='w')

        slider_widget, sub_slider_widget = create_slider_with_subslider(track_row_frame, slider_file, secondary_slider_file)
        sliders.append(slider_widget)
        secondary_sliders.append(sub_slider_widget)
        slider_widget.canvas.grid(row=0, column=1, columnspan=4, sticky='ew')
        track_row_frame.grid_columnconfigure(1, weight=1)

        slider_widget.set_main(current_sound_levels.get(i, 0.0))
        sub_slider_widget.set_sub(current_threshold_levels.get(i, 0.5))

        for j in range(4):
            check_var = tk.IntVar(value=current_checkbox_states.get(i, [0,0,0,0])[j])
            chkbox = ttk.Checkbutton(track_row_frame, variable=check_var, text=str(j+1),
                                     command=lambda slider_idx=i, box_idx=j: checkbox_clicked(slider_idx, box_idx),
                                     style='TCheckbutton')
            chkbox.grid(row=1, column=j+1, padx=2, pady=2, sticky='w')
            check_vars[i][j] = check_var


    update_highlight(buttons, 'input.txt', active_cameras)
    root.after(250, lambda: update_sliders_from_files(secondary_sliders, secondary_slider_files, is_sub=True))

    root.mainloop()

def main():
    global server, client, root, number_of_tracks
    update_input_file('automated.txt', 1)

    connection_to_switcher()

    osc_client_port = 11000
    osc_server_base_port = 11001

    client = udp_client.SimpleUDPClient("127.0.0.1", osc_client_port)

    disp = dispatcher.Dispatcher()
    current_server_port = osc_server_base_port
    max_attempts = 5
    for attempt in range(max_attempts):
        if not is_port_in_use(current_server_port):
            break
        print(current_time() + CRED_RED + f" Port {current_server_port} is in use. Attempting to kill the process..." + CEND)
        if kill_port_process(current_server_port):
            if not is_port_in_use(current_server_port):
                print(current_time() + CRED_RED + f" Port {current_server_port} successfully freed." + CEND)
                break
        print(current_time() + CRED_RED + f" Failed to free port {current_server_port}. Trying next port..." + CEND)
        current_server_port += 1
        if attempt == max_attempts - 1:
            print(current_time() + CRED_RED + f" All port attempts failed (tried {osc_server_base_port} to {current_server_port}). Exiting." + CEND)
            cleanup()
            return

    try:
        print(current_time() + CRED_RED + f" Starting OSC server on port {current_server_port}" + CEND)
        server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", current_server_port), disp)
        print(current_time() + CRED_RED + f" OSC server started on port {current_server_port}" + CEND)
    except OSError as e:
        print(current_time() + CRED_RED + f" Failed to start OSC server on port {current_server_port}: {e}" + CEND)
        cleanup()
        return

    disp.map("/live/track/get/output_meter_level", osc_handler)
    disp.map("/live/song/get/num_tracks", osc_handler)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    main_values_thread = threading.Thread(target=ableton_track_level, daemon=True)
    main_values_thread.start()

    camera_brain_thread = threading.Thread(target=camera_brain, daemon=True)
    camera_brain_thread.start()

    print(f"{current_time()} Requesting initial number of tracks from Ableton...")
    client.send_message("/live/song/get/num_tracks", 0)
    time.sleep(1)

    with data_lock:
        for k in range(number_of_tracks):
            current_sound_levels[k] = read_value_from_file(f"Track_{k}_status.txt")
            current_threshold_levels[k] = read_value_from_file(f"Secondary_Track_{k}_status.txt")
            current_checkbox_states[k] = read_checkbox_states(k)

    gui()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    try:
        main()
    except KeyboardInterrupt:
        cleanup()