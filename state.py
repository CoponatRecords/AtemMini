"""The single source of truth for everything the threads share.

The old version passed data between threads by writing ~100 little
.txt files and re-reading them four times a second. That works *most*
of the time — and "most of the time" is exactly what intermittent bugs
are made of: a reader that catches a file half-written gets a silent
default value back, the threshold slider fights your mouse because a
poll loop keeps re-reading the old file, and the disk churns nonstop.

The fix: threads in one process don't need files to talk. All shared
data lives in this one object, and every access takes `self.lock` so
two threads never read/write the same value mid-update.

The only thing that still touches disk is save()/load(): the USER's
settings (thresholds, camera mappings, active cameras) go into a
single settings.json so they survive a restart. Live data (meter
levels) is never persisted — it is worthless one second later.
"""

import json
import threading
import time
from collections import deque

import config


class AppState:
    def __init__(self):
        self.lock = threading.Lock()

        # --- live data from Ableton (never persisted) ---
        self.num_tracks = 0
        self.levels = {}          # track index -> latest meter level (0..1)
        self.level_history = {}   # track index -> deque of (timestamp, level)

        # --- user settings (persisted in settings.json) ---
        self.thresholds = {}      # track index -> threshold (0..1)
        self.track_cameras = {}   # track index -> [0/1] per camera
        self.active_cameras = [1] * config.NUM_CAMERAS
        self.automated = True

        # --- switching status ---
        self.current_camera = None
        self.last_switch_time = 0.0

    # ---- live meter data -------------------------------------------

    def set_level(self, track, level):
        """Store the newest meter level and keep a short history so the
        brain can judge average loudness instead of a single instant."""
        now = time.monotonic()
        with self.lock:
            self.levels[track] = level
            history = self.level_history.setdefault(track, deque())
            history.append((now, level))
            cutoff = now - config.METER_WINDOW
            while history and history[0][0] < cutoff:
                history.popleft()

    def average_level(self, track):
        with self.lock:
            history = self.level_history.get(track)
            if not history:
                return 0.0
            return sum(level for _, level in history) / len(history)

    def set_num_tracks(self, n):
        """Returns True if the track count changed (GUI wants to know)."""
        with self.lock:
            changed = n != self.num_tracks
            self.num_tracks = n
            return changed

    # ---- user settings ---------------------------------------------

    def get_threshold(self, track):
        with self.lock:
            return self.thresholds.get(track, 0.5)

    def set_threshold(self, track, value):
        with self.lock:
            self.thresholds[track] = value

    def get_track_cameras(self, track):
        with self.lock:
            return list(self.track_cameras.get(track, [0] * config.NUM_CAMERAS))

    def set_track_camera(self, track, camera_index, enabled):
        with self.lock:
            boxes = self.track_cameras.setdefault(
                track, [0] * config.NUM_CAMERAS)
            boxes[camera_index] = 1 if enabled else 0
        self.save()

    def is_camera_active(self, camera_number):
        with self.lock:
            return self.active_cameras[camera_number - 1] == 1

    def toggle_camera_active(self, camera_index):
        with self.lock:
            self.active_cameras[camera_index] ^= 1
            result = self.active_cameras[camera_index]
        self.save()
        return result

    def set_automated(self, on):
        with self.lock:
            self.automated = bool(on)
        self.save()

    def is_automated(self):
        with self.lock:
            return self.automated

    # ---- switching status ------------------------------------------

    def record_switch(self, camera_number):
        with self.lock:
            self.current_camera = camera_number
            self.last_switch_time = time.monotonic()

    def get_switch_status(self):
        with self.lock:
            return self.current_camera, self.last_switch_time

    # ---- persistence -----------------------------------------------

    def save(self):
        with self.lock:
            data = {
                # JSON keys must be strings, so convert the track indexes
                "thresholds": {str(k): v for k, v in self.thresholds.items()},
                "track_cameras": {str(k): v for k, v in self.track_cameras.items()},
                "active_cameras": self.active_cameras,
                "automated": self.automated,
            }
        try:
            with open(config.SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            print(f"Could not save {config.SETTINGS_FILE}: {e}")

    def load(self):
        try:
            with open(config.SETTINGS_FILE) as f:
                data = json.load(f)
        except FileNotFoundError:
            return  # first run — defaults are fine
        except (OSError, json.JSONDecodeError) as e:
            print(f"Could not read {config.SETTINGS_FILE}: {e} — using defaults")
            return
        with self.lock:
            self.thresholds = {int(k): float(v)
                               for k, v in data.get("thresholds", {}).items()}
            self.track_cameras = {int(k): list(v)
                                  for k, v in data.get("track_cameras", {}).items()}
            active = data.get("active_cameras")
            if isinstance(active, list) and len(active) == config.NUM_CAMERAS:
                self.active_cameras = [1 if x else 0 for x in active]
            self.automated = bool(data.get("automated", True))
