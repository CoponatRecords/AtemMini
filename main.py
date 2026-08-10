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

import config
from state import AppState

# PyATEMMax is an external dependency, assuming it is installed.
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

# Global objects
state = AppState()
switcher = PyATEMMax.ATEMMax()
server = None
client = None

root = None
sliders = []
start_stop_btn = None
start_icon = None
pause_icon = None

# ANSI color codes for terminal (for console output, not GUI)
CRED_RED = '\033[91m'
CEND = '\033[0m'


# --- Helper Functions ---
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


# --- ATEM Mini Control (using PyATEMMax) ---
def connection_to_switcher():
    print(current_time() + CRED_RED + " Connecting to ATEM Mini..." + CEND)
    try:
        switcher.connect(config.ATEM_IP)
        switcher.waitForConnection()
        print(current_time() + CRED_RED + " Connected to ATEM Mini" + CEND)
    except Exception as e:
        print(current_time() + CRED_RED + f" Failed to connect to ATEM Mini: {e}" + CEND)

def disconnect_switcher():
    try:
        switcher.disconnect()
        print(current_time() + CRED_RED + " Disconnected from ATEM Mini" + CEND)
    except Exception as e:
        print(current_time() + CRED_RED + f" Error disconnecting from ATEM Mini: {e}" + CEND)

def camera(n):
    """Cut to camera n: put it on preview, then run the Auto transition."""
    try:
        switcher.setPreviewInputVideoSource(0, n)
        switcher.execAutoME(0)
        print(f"Camera {n} selected")
        state.record_switch(n)
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
    if args[0] == '/live/song/get/num_tracks':
        print(current_time() + 'Number of tracks - ' + str(args[1]))
        state.set_num_tracks(int(args[1]))
    elif args[0] == '/live/track/get/output_meter_level':
        n = int(args[-2])
        level = float(args[-1])
        state.set_level(n, level)

        if root and sliders and n < len(sliders):
            root.after_idle(lambda: sliders[n].set_main(level))

# --- Core Logic Functions ---
def ableton_track_level():
    client.send_message("/live/song/get/num_tracks", 0)
    time.sleep(0.5)

    while True:
        with state.lock:
            num_tracks = state.num_tracks
        for k in range(num_tracks):
            client.send_message("/live/track/get/output_meter_level", k)
        time.sleep(config.METER_POLL_INTERVAL)

def camera_brain():
    print(current_time() + "Brain Started")

    while True:
        if state.is_automated():
            with state.lock:
                num_tracks = state.num_tracks

            # Every track that is currently louder than its threshold
            # "votes" for the cameras it is mapped to.
            camera_votes = [0] * config.NUM_CAMERAS
            for k in range(num_tracks):
                with state.lock:
                    sound = state.levels.get(k, 0.0)
                if state.get_threshold(k) < sound:
                    boxes = state.get_track_cameras(k)
                    for cam_idx in range(config.NUM_CAMERAS):
                        if boxes[cam_idx] == 1:
                            camera_votes[cam_idx] += 1

            # More votes -> more entries in the list -> higher chance.
            cam_list = []
            for i, votes in enumerate(camera_votes):
                cam_list.extend([i + 1] * votes)

            filtered_cam_list = [cam for cam in cam_list
                                 if state.is_camera_active(cam)]

            if filtered_cam_list:
                print(f'{current_time()} Camera mix candidates: {filtered_cam_list}')
                camera(random.choice(filtered_cam_list))
            else:
                print(f'{current_time()} AutoSwitch is not changing any cameras at the moment (no sound above threshold or no active cameras chosen for tracks).')
        time.sleep(config.DECISION_INTERVAL)

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


def update_highlight(buttons):
    """Light up the button of the camera that is currently on air."""
    current_camera, _ = state.get_switch_status()
    if current_camera is not None:
        highlight_button(buttons, current_camera - 1)
    if root:
        root.after(250, update_highlight, buttons)

def toggle_automated():
    global start_stop_btn, start_icon, pause_icon
    new_value = not state.is_automated()
    state.set_automated(new_value)
    print(f"{current_time()} Automated switching: {'on' if new_value else 'off'}")

    if start_stop_btn:
        start_stop_btn.config(image=pause_icon if new_value else start_icon, text="")

def toggle_camera(idx, buttons):
    state.toggle_camera_active(idx)
    update_camera_button_style(idx, buttons)

def update_camera_button_style(idx, buttons):
    if state.is_camera_active(idx + 1):
        buttons[idx].configure(state=tk.NORMAL, style='Camera.TButton')
        buttons[idx].config(command=lambda idx=idx: camera(idx + 1))
    else:
        buttons[idx].configure(state=tk.DISABLED, style='Disabled.TButton')
        buttons[idx].config(command=None)

def checkbox_clicked(track_idx, box_idx, check_var):
    state.set_track_camera(track_idx, box_idx, check_var.get())

def highlight_button(buttons, selected_index):
    for idx, btn in enumerate(buttons):
        if state.is_camera_active(idx + 1):
            btn.configure(style='Camera.TButton')
    if 0 <= selected_index < len(buttons) and state.is_camera_active(selected_index + 1):
        buttons[selected_index].configure(style='Red.TButton')

# --- Main GUI Function ---
def gui():
    global root, start_stop_btn, start_icon, pause_icon, sliders

    root = ThemedTk(theme="arc")
    root.title("Aperture Control")
    root.attributes('-topmost', True)
    root.configure(bg="#1a1a1a")

    # --- Styling Configuration ---
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
              background=[('pressed', '#333333'), ('active', '#555555'), ('!disabled', '#444444')],
              foreground=[('!disabled', 'green')])

    # Camera buttons (Normal/Active)
    style.configure('Camera.TButton', font=button_font, foreground="black")
    style.map('Camera.TButton',
              background=[('pressed', '#005bb5'), ('active', '#34aadc'), ('!disabled', '#007aff')],
              foreground=[('!disabled', 'green')])

    # Highlighted (Selected) camera button
    style.configure('Red.TButton', font=button_font, foreground="red")
    style.map('Red.TButton',
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

    # Frame for Camera Control Buttons
    camera_control_frame = ttk.Frame(root, padding="15 10", style='TFrame')
    camera_control_frame.pack(fill=tk.X, pady=(15, 5))

    buttons = []
    for i, label_text in enumerate(cam_labels):
        btn = ttk.Button(camera_control_frame, text=label_text, command=lambda idx=i: toggle_camera(idx, buttons))
        btn.grid(row=0, column=i, padx=5, pady=5, sticky='ew')
        buttons.append(btn)
        update_camera_button_style(i, buttons)

    for i in range(len(cam_labels)):
        camera_control_frame.grid_columnconfigure(i, weight=1)


    # Frame for Global Automation Toggle
    auto_control_frame = ttk.Frame(root, padding="15 10", style='TFrame')
    auto_control_frame.pack(fill=tk.X, pady=5)

    start_icon = resize_image("start_icon.png", 24, 24)
    pause_icon = resize_image("stop_icon.png", 24, 24)

    start_stop_btn = ttk.Button(auto_control_frame, image=pause_icon, text="", compound=tk.LEFT,
                                command=toggle_automated, style='TButton')
    start_stop_btn.pack(pady=10, expand=True)

    start_stop_btn.config(image=pause_icon if state.is_automated() else start_icon, text="")

    # Frame for Sliders and Checkboxes
    sliders_checkboxes_frame = ttk.Frame(root, padding="15 10", style='TFrame')
    sliders_checkboxes_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    sliders.clear()

    with state.lock:
        num_tracks = state.num_tracks

    for i in range(num_tracks):
        track_row_frame = ttk.Frame(sliders_checkboxes_frame, padding="0 5", style='TFrame')
        track_row_frame.pack(fill=tk.X, expand=True, pady=5)

        name_label = ttk.Label(track_row_frame, text=f"Track {i}", style='TLabel')
        name_label.grid(row=0, column=0, padx=(0,10), sticky='w')

        slider = CustomDualSlider(track_row_frame)
        # When the user releases the threshold thumb, store the new value.
        slider.bind_sub(lambda i=i, s=slider: (state.set_threshold(i, s.subget()),
                                               state.save()))
        sliders.append(slider)
        slider.canvas.grid(row=0, column=1, columnspan=4, sticky='ew')
        track_row_frame.grid_columnconfigure(1, weight=1)

        with state.lock:
            level = state.levels.get(i, 0.0)
        slider.set_main(level)
        slider.set_sub(state.get_threshold(i))

        for j in range(config.NUM_CAMERAS):
            check_var = tk.IntVar(value=state.get_track_cameras(i)[j])
            chkbox = ttk.Checkbutton(track_row_frame, variable=check_var, text=str(j+1),
                                     command=lambda i=i, j=j, v=check_var: checkbox_clicked(i, j, v),
                                     style='TCheckbutton')
            chkbox.grid(row=1, column=j+1, padx=2, pady=2, sticky='w')

    update_highlight(buttons)

    root.mainloop()

def main():
    global server, client

    state.load()

    connection_to_switcher()

    client = udp_client.SimpleUDPClient(config.OSC_HOST, config.OSC_SEND_PORT)

    disp = dispatcher.Dispatcher()
    current_server_port = config.OSC_LISTEN_PORT
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
            print(current_time() + CRED_RED + f" All port attempts failed. Exiting." + CEND)
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

    gui()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    try:
        main()
    except KeyboardInterrupt:
        cleanup()
