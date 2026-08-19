"""Wires the pieces together and starts the app.

Each module has exactly one job:

    config.py   - every tweakable value (IPs, ports, timings)
    state.py    - AppState: the shared data, behind one lock
    ableton.py  - AbletonLink: OSC in/out, fills AppState with meters
    atem.py     - Switcher: ATEM connection + reconnect watchdog
    brain.py    - decides which camera should be on air
    gui.py      - the window; other threads reach it ONLY via gui_queue

Data flows one way:

    Ableton --OSC--> AppState --> brain --> Switcher --> ATEM
                        |                      |
                        +-----> gui_queue <----+
                                   |
                                  GUI
"""

import queue
import signal
import sys
import threading

from state import AppState
from ableton import AbletonLink
from atem import Switcher
import brain
import gui


def main():
    state = AppState()
    state.load()

    gui_queue = queue.Queue()

    switcher = Switcher(state,
                        on_switch=lambda n: gui_queue.put(("camera", n)))
    switcher.start()

    ableton = AbletonLink(
        state,
        on_meter=lambda track, level: gui_queue.put(("meter", track, level)),
        on_track_count=lambda n: gui_queue.put(("tracks", n)))
    ableton.start()

    stop_brain = threading.Event()
    threading.Thread(target=brain.run, args=(state, switcher, stop_brain),
                     daemon=True, name="brain").start()

    # Blocks until the window is closed.
    gui.run(state, switcher, gui_queue)

    print("Shutting down...")
    stop_brain.set()
    ableton.stop()
    switcher.stop()
    state.save()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    main()
