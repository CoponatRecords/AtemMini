"""Talks to Ableton Live through AbletonOSC.

One job: keep AppState filled with fresh data from Ableton.

- We SEND requests to config.OSC_SEND_PORT (AbletonOSC listens there).
- We LISTEN for replies on config.OSC_LISTEN_PORT.
- A poller thread asks for every track's meter level 10x/second, and
  re-asks for the track count every few seconds — so starting Ableton
  AFTER this app now works: the GUI picks the tracks up as soon as
  Ableton answers, instead of staying empty forever.

On the port question: the old code found whatever process was
listening on our port and killed it with SIGKILL. That "worked" when
the process was a leftover copy of this app — but 'kill whatever is on
the port, no questions asked' is a foot-gun aimed at everything else
on the machine. If the port is taken we now say so, say by whom the
user should look for, and exit. Closing a stray program yourself takes
five seconds and doesn't shoot anything in the head.
"""

import sys
import threading
import time

from pythonosc import dispatcher, osc_server, udp_client

import config


class AbletonLink:
    def __init__(self, state, on_meter=None, on_track_count=None):
        """on_meter(track, level) and on_track_count(n) are optional
        callbacks so the GUI can react to fresh data."""
        self.state = state
        self.on_meter = on_meter
        self.on_track_count = on_track_count
        self.client = udp_client.SimpleUDPClient(
            config.OSC_HOST, config.OSC_SEND_PORT)
        self.server = None
        self._stop = threading.Event()

    # ---- lifecycle --------------------------------------------------

    def start(self):
        disp = dispatcher.Dispatcher()
        disp.map("/live/track/get/output_meter_level", self._handle_meter)
        disp.map("/live/song/get/num_tracks", self._handle_track_count)

        try:
            self.server = osc_server.ThreadingOSCUDPServer(
                (config.OSC_HOST, config.OSC_LISTEN_PORT), disp)
        except OSError:
            print(f"Port {config.OSC_LISTEN_PORT} is already in use.\n"
                  f"Most likely another copy of this program is still "
                  f"running — close it and start again.")
            sys.exit(1)

        threading.Thread(target=self.server.serve_forever,
                         daemon=True, name="osc-server").start()
        threading.Thread(target=self._poller,
                         daemon=True, name="osc-poller").start()
        print(f"Listening for Ableton on port {config.OSC_LISTEN_PORT}")

    def stop(self):
        self._stop.set()
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    # ---- incoming messages ------------------------------------------

    def _handle_meter(self, address, *args):
        track = int(args[-2])
        level = float(args[-1])
        self.state.set_level(track, level)
        if self.on_meter:
            self.on_meter(track, level)

    def _handle_track_count(self, address, *args):
        n = int(args[0])
        if self.state.set_num_tracks(n):
            print(f"Ableton reports {n} tracks")
            if self.on_track_count:
                self.on_track_count(n)

    # ---- outgoing requests ------------------------------------------

    def _poller(self):
        """Ask Ableton for data on a fixed beat."""
        last_track_poll = 0.0
        while not self._stop.is_set():
            now = time.monotonic()
            if now - last_track_poll >= config.TRACK_POLL_INTERVAL:
                self.client.send_message("/live/song/get/num_tracks", 0)
                last_track_poll = now
            with self.state.lock:
                num_tracks = self.state.num_tracks
            for k in range(num_tracks):
                self.client.send_message(
                    "/live/track/get/output_meter_level", k)
            time.sleep(config.METER_POLL_INTERVAL)
