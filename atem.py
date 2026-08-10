"""Connection to the ATEM Mini, with automatic reconnection.

The old code connected once at startup and never looked back:

- waitForConnection() with no timeout blocks FOREVER if the switcher
  is off or unreachable — the app just hung with no window.
- If the connection dropped mid-stream (Wi-Fi blip, cable, switcher
  reboot), nothing noticed. camera() kept "succeeding" into the void
  and auto-switching silently stopped until someone restarted the app.

Rule for anything that must survive a live show: never assume a
network connection stays up. Connect with a timeout, notice when the
link dies, and quietly keep retrying in the background. That is the
whole job of the watchdog thread below.
"""

import threading
import time

import config

try:
    import PyATEMMax
    HAVE_PYATEMMAX = True
except ImportError:
    print("PyATEMMax not installed — running without a real switcher. "
          "Camera cuts will only be printed.")
    HAVE_PYATEMMAX = False


class Switcher:
    def __init__(self, state, on_switch=None):
        """on_switch(camera_number) is an optional callback so the GUI
        can highlight the camera that just went on air."""
        self.state = state
        self.on_switch = on_switch
        self.atem = PyATEMMax.ATEMMax() if HAVE_PYATEMMAX else None
        self._stop = threading.Event()
        self._was_connected = False

    # ---- lifecycle --------------------------------------------------

    def start(self):
        """Start the background thread that owns the connection."""
        threading.Thread(target=self._watchdog,
                         daemon=True, name="atem-watchdog").start()

    def stop(self):
        self._stop.set()
        if self.atem is not None:
            try:
                self.atem.disconnect()
            except Exception:
                pass

    def is_connected(self):
        return self.atem is not None and self.atem.connected

    # ---- the watchdog -----------------------------------------------

    def _watchdog(self):
        """Keep the connection alive. Runs forever in the background:
        not connected -> try to connect (with a timeout, so a switched-
        off ATEM can never hang the app) -> report changes -> sleep."""
        if self.atem is None:
            return
        while not self._stop.is_set():
            if not self.atem.connected:
                if self._was_connected:
                    print("Lost connection to the ATEM — reconnecting...")
                    self._was_connected = False
                try:
                    self.atem.connect(config.ATEM_IP)
                    self.atem.waitForConnection(
                        infinite=False, timeout=config.ATEM_CONNECT_TIMEOUT)
                except Exception as e:
                    print(f"ATEM connection attempt failed: {e}")
                if self.atem.connected:
                    print(f"Connected to ATEM at {config.ATEM_IP}")
                    self._was_connected = True
                else:
                    self.atem.disconnect()  # clean up the failed attempt
            self._stop.wait(config.ATEM_RECONNECT_INTERVAL)

    # ---- switching --------------------------------------------------

    def cut_to(self, camera_number):
        """Cut to a camera: put it on preview, then run the Auto
        transition. Returns True if the command was actually sent."""
        if self.atem is None:
            print(f"(no switcher) would cut to camera {camera_number}")
            self.state.record_switch(camera_number)
            if self.on_switch:
                self.on_switch(camera_number)
            return True
        if not self.atem.connected:
            print(f"Not connected to the ATEM — cannot cut to "
                  f"camera {camera_number}")
            return False
        try:
            self.atem.setPreviewInputVideoSource(0, camera_number)
            self.atem.execAutoME(0)
        except Exception as e:
            print(f"ATEM command failed: {e}")
            return False
        print(f"Cut to camera {camera_number}")
        self.state.record_switch(camera_number)
        if self.on_switch:
            self.on_switch(camera_number)
        return True
