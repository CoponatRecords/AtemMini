"""The window: camera buttons, start/stop, one row per Ableton track.

The one rule that matters in this file: **only the main thread may
touch Tkinter.** Tk is not thread-safe — the old code called into the
GUI from the OSC thread ten times a second per track, which works
right up until it crashes with "main thread is not in main loop" (or
just segfaults). Those crashes look random; they aren't.

The fix is the standard pattern for every GUI toolkit ever made:
other threads put messages on a queue.Queue (which IS thread-safe),
and the GUI drains that queue from its own event loop every 50 ms.
Data crosses the thread boundary through the queue, nothing else.

Controls:
  - Left-click a camera button  = cut to that camera now.
  - Right-click a camera button = enable/disable it for the
    auto-switcher (grayed out = the brain will never pick it).
  - Per track: drag the white thumb to set the loudness threshold,
    tick the numbers to map the track to cameras.

The track rows are (re)built whenever Ableton reports a track count —
so the window is no longer empty forever when Ableton starts late.
"""

import queue
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk, ImageDraw

try:
    from ttkthemes import ThemedTk
except ImportError:
    ThemedTk = None

import config


class CustomDualSlider:
    """One track row's meter bar (drawn) + threshold thumb (draggable)."""

    def __init__(self, parent, from_=0.0, to=1.0):
        self.from_ = from_
        self.to = to
        self.width = 400
        self.height = 20
        self.thumb_size = 10

        self.canvas = tk.Canvas(parent, width=self.width, height=self.height,
                                highlightthickness=0, bg="#1a1a1a", bd=0)
        self.value_main = from_
        self.value_sub = from_

        self.track = self.canvas.create_rectangle(
            0, 9, self.width, 11, fill="#555555", outline="")
        self.fill_sub = self.canvas.create_rectangle(
            0, 0, 0, self.height, fill="#777777", outline="")
        self.fill_main = self.canvas.create_rectangle(
            0, 8, 0, 12, fill="#007aff", outline="")
        self.thumb_sub = self.canvas.create_oval(
            0, 2, self.thumb_size, 18, fill="white", outline="#999999")

        self.drag_indicator = None

        self.canvas.tag_bind(self.thumb_sub, "<Button-1>", self.start_drag_sub)
        self.canvas.tag_bind(self.thumb_sub, "<B1-Motion>", self.move_sub)
        self.canvas.tag_bind(self.thumb_sub, "<ButtonRelease-1>", self.release_sub)
        self.canvas.bind("<Button-1>", self.start_drag_sub)
        self.canvas.bind("<B1-Motion>", self.move_sub)
        self.canvas.bind("<ButtonRelease-1>", self.release_sub)

        self.command_sub = None
        self.set_main(from_)
        self.set_sub(from_)

    def _thumb_x(self):
        return ((self.value_sub - self.from_) / (self.to - self.from_)
                * (self.width - self.thumb_size) + self.thumb_size / 2)

    def start_drag_sub(self, event):
        self.move_sub_value_from_event(event)
        if self.drag_indicator:
            self.canvas.delete(self.drag_indicator)
        x = self._thumb_x()
        self.drag_indicator = self.canvas.create_rectangle(
            x - 1, 0, x + 1, self.height, fill="#bbbbbb", outline="")

    def move_sub_value_from_event(self, event):
        x = max(0, min(self.width - self.thumb_size,
                       event.x - self.thumb_size / 2))
        new_value = self.from_ + (x / (self.width - self.thumb_size)) \
            * (self.to - self.from_)
        self.set_sub(new_value)

    def move_sub(self, event):
        self.move_sub_value_from_event(event)
        if self.drag_indicator:
            x = self._thumb_x()
            self.canvas.coords(self.drag_indicator, x - 1, 0, x + 1, self.height)

    def release_sub(self, event):
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

    def set_sub(self, value):
        self.value_sub = max(self.from_, min(self.to, float(value)))
        x_thumb = (self.value_sub - self.from_) / (self.to - self.from_) \
            * (self.width - self.thumb_size)
        self.canvas.coords(self.thumb_sub, x_thumb, 2,
                           x_thumb + self.thumb_size, 18)
        self.canvas.coords(self.fill_sub, x_thumb + self.thumb_size / 2, 0,
                           x_thumb + self.thumb_size / 2, self.height)
        self.update_fill_color()

    def update_fill_color(self):
        color = "#34c759" if self.value_main > self.value_sub else "#ff453a"
        self.canvas.itemconfig(self.fill_main, fill=color)

    def subget(self):
        return self.value_sub

    def bind_sub(self, command):
        self.command_sub = command


class AppGui:
    def __init__(self, state, switcher, gui_queue):
        self.state = state
        self.switcher = switcher
        self.queue = gui_queue
        self.sliders = []
        self.cam_buttons = []

        if ThemedTk is not None:
            self.root = ThemedTk(theme="arc")
        else:
            self.root = tk.Tk()
        self.root.title("Aperture Control")
        self.root.attributes('-topmost', True)
        self.root.configure(bg="#1a1a1a")

        self._build_styles()
        self._build_camera_buttons()
        self._build_start_stop()
        self.tracks_frame = ttk.Frame(self.root, padding="15 10", style='TFrame')
        self.tracks_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        with self.state.lock:
            num_tracks = self.state.num_tracks
        self._build_track_rows(num_tracks)

    # ---- construction ----------------------------------------------

    def _build_styles(self):
        style = ttk.Style()
        if ThemedTk is not None:
            style.theme_use("arc")

        app_font = ('Helvetica Neue', 10)
        button_font = ('Helvetica Neue', 11)

        style.configure('.', font=app_font, background="#1a1a1a",
                        foreground="#cccccc")
        style.map('.', background=[('disabled', '#333333')])

        style.configure('TButton', font=button_font, padding=[10, 5],
                        relief="flat", focuscolor="#444444", focusthickness=0,
                        bordercolor="#555555", borderwidth=1)
        style.map('TButton',
                  background=[('pressed', '#333333'), ('active', '#555555'),
                              ('!disabled', '#444444')],
                  foreground=[('!disabled', 'green')])

        # Camera enabled for the auto-switcher
        style.configure('Camera.TButton', font=button_font, foreground="black")
        style.map('Camera.TButton',
                  background=[('pressed', '#005bb5'), ('active', '#34aadc'),
                              ('!disabled', '#007aff')],
                  foreground=[('!disabled', 'green')])

        # Camera currently on air
        style.configure('Red.TButton', font=button_font, foreground="red")
        style.map('Red.TButton',
                  background=[('pressed', '#cc382e'), ('active', 'red'),
                              ('!disabled', '#ff453a')],
                  foreground=[('!disabled', 'red')])

        # Camera excluded from the auto-switcher
        style.configure('Off.TButton', font=button_font, relief="flat")
        style.map('Off.TButton',
                  background=[('!disabled', '#555555')],
                  foreground=[('!disabled', '#aaaaaa')])

        style.configure('TLabel', font=app_font, background="#1a1a1a",
                        foreground="#cccccc")
        style.configure('TCheckbutton', font=app_font, background="black",
                        foreground="#cccccc", indicatoron=False,
                        relief="flat", padding=[5, 5])
        style.map('TCheckbutton',
                  background=[('selected', 'grey'), ('!selected', 'grey'),
                              ('active', 'grey')],
                  foreground=[('selected', '#ffffff'), ('!selected', '#cccccc')])

    def _build_camera_buttons(self):
        frame = ttk.Frame(self.root, padding="15 10", style='TFrame')
        frame.pack(fill=tk.X, pady=(15, 5))
        for i in range(config.NUM_CAMERAS):
            btn = ttk.Button(frame, text=f"Cam {i + 1}",
                             command=lambda n=i + 1: self.switcher.cut_to(n))
            btn.grid(row=0, column=i, padx=5, pady=5, sticky='ew')
            # Right-click toggles whether the auto-switcher may use it.
            btn.bind("<Button-2>", lambda e, i=i: self._toggle_camera(i))
            btn.bind("<Button-3>", lambda e, i=i: self._toggle_camera(i))
            frame.grid_columnconfigure(i, weight=1)
            self.cam_buttons.append(btn)
        self._refresh_camera_styles()

    def _build_start_stop(self):
        frame = ttk.Frame(self.root, padding="15 10", style='TFrame')
        frame.pack(fill=tk.X, pady=5)
        self.start_icon = self._load_icon("start_icon.png")
        self.pause_icon = self._load_icon("stop_icon.png")
        self.start_stop_btn = ttk.Button(frame, image=self.pause_icon,
                                         command=self._toggle_automated,
                                         style='TButton')
        self.start_stop_btn.pack(pady=10, expand=True)
        self._refresh_start_stop()

    def _load_icon(self, path, size=24):
        try:
            img = Image.open(path).resize((size, size), Image.LANCZOS)
        except FileNotFoundError:
            img = Image.new('RGB', (size, size), color='gray')
            ImageDraw.Draw(img).text((4, 6), "?", fill=(0, 0, 0))
        return ImageTk.PhotoImage(img)

    def _build_track_rows(self, num_tracks):
        """(Re)build one row per Ableton track. Called at startup and
        again whenever Ableton reports a different track count."""
        for child in self.tracks_frame.winfo_children():
            child.destroy()
        self.sliders = []

        for i in range(num_tracks):
            row = ttk.Frame(self.tracks_frame, padding="0 5", style='TFrame')
            row.pack(fill=tk.X, expand=True, pady=5)

            ttk.Label(row, text=f"Track {i}", style='TLabel').grid(
                row=0, column=0, padx=(0, 10), sticky='w')

            slider = CustomDualSlider(row)
            slider.bind_sub(lambda i=i, s=slider: self._threshold_changed(i, s))
            slider.canvas.grid(row=0, column=1, columnspan=config.NUM_CAMERAS,
                               sticky='ew')
            row.grid_columnconfigure(1, weight=1)
            slider.set_sub(self.state.get_threshold(i))
            self.sliders.append(slider)

            for j in range(config.NUM_CAMERAS):
                var = tk.IntVar(value=self.state.get_track_cameras(i)[j])
                box = ttk.Checkbutton(
                    row, variable=var, text=str(j + 1),
                    command=lambda i=i, j=j, v=var:
                        self.state.set_track_camera(i, j, v.get()),
                    style='TCheckbutton')
                box.grid(row=1, column=j + 1, padx=2, pady=2, sticky='w')
                box.var = var  # keep a reference or tk garbage-collects it

    # ---- user actions ----------------------------------------------

    def _threshold_changed(self, track, slider):
        self.state.set_threshold(track, slider.subget())
        self.state.save()

    def _toggle_camera(self, idx):
        self.state.toggle_camera_active(idx)
        self._refresh_camera_styles()

    def _toggle_automated(self):
        self.state.set_automated(not self.state.is_automated())
        self._refresh_start_stop()

    # ---- display updates -------------------------------------------

    def _refresh_start_stop(self):
        on = self.state.is_automated()
        self.start_stop_btn.config(
            image=self.pause_icon if on else self.start_icon)

    def _refresh_camera_styles(self):
        current, _ = self.state.get_switch_status()
        for idx, btn in enumerate(self.cam_buttons):
            if idx + 1 == current:
                btn.configure(style='Red.TButton')
            elif self.state.is_camera_active(idx + 1):
                btn.configure(style='Camera.TButton')
            else:
                btn.configure(style='Off.TButton')

    # ---- the queue drain: the ONLY door into the GUI ---------------

    def _drain_queue(self):
        """Handle everything other threads posted since last time.
        Runs on the Tk main thread, every 50 ms."""
        try:
            while True:
                message = self.queue.get_nowait()
                kind = message[0]
                if kind == "meter":
                    _, track, level = message
                    if track < len(self.sliders):
                        self.sliders[track].set_main(level)
                elif kind == "tracks":
                    self._build_track_rows(message[1])
                elif kind == "camera":
                    self._refresh_camera_styles()
        except queue.Empty:
            pass
        self.root.after(50, self._drain_queue)

    def run(self):
        self.root.after(50, self._drain_queue)
        self.root.mainloop()


def run(state, switcher, gui_queue):
    AppGui(state, switcher, gui_queue).run()
