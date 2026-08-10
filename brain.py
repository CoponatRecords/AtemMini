"""Decides which camera should be on air.

How a decision works, every DECISION_INTERVAL seconds:

1. Every track whose AVERAGE loudness (over the last METER_WINDOW
   seconds) is above its threshold "votes" for the cameras it is
   mapped to. More votes -> higher chance.
2. Votes for cameras that are switched off in the GUI are dropped.
3. Votes for the camera that is ALREADY on air are dropped too — a
   "cut" to the same shot looks like nothing happened and wastes the
   turn. If the current camera is the only candidate, staying on it
   is the right call anyway.
4. If we cut away only MIN_SHOT_SECONDS ago, wait — nervous cutting
   looks worse than a shot that lingers slightly long.
5. Pick one of the remaining votes at random and cut.

Why the average instead of the instantaneous level (what the old code
used): the old brain sampled ONE instant every 10 seconds. Sample
between two drum hits and the drums count as silent; sample during a
single cough and a quiet stage looks loud. Averaging over a couple of
seconds judges what the viewer actually heard, not one unlucky
millisecond.
"""

import random
import time

import config


def choose_camera(state):
    """One decision. Returns a camera number, or None for 'no cut'.
    Pure logic, no waiting and no hardware — so you can test it by
    just calling it."""
    with state.lock:
        num_tracks = state.num_tracks

    votes = []
    for track in range(num_tracks):
        if state.average_level(track) > state.get_threshold(track):
            boxes = state.get_track_cameras(track)
            for cam_idx, mapped in enumerate(boxes):
                if mapped:
                    votes.append(cam_idx + 1)

    current_camera, _ = state.get_switch_status()
    candidates = [cam for cam in votes
                  if state.is_camera_active(cam) and cam != current_camera]
    if not candidates:
        return None
    return random.choice(candidates)


def run(state, switcher, stop_event):
    """The brain thread: decide, cut, wait, repeat — until told to stop."""
    print("Brain started")
    while not stop_event.wait(config.DECISION_INTERVAL):
        if not state.is_automated():
            continue

        _, last_switch = state.get_switch_status()
        if time.monotonic() - last_switch < config.MIN_SHOT_SECONDS:
            continue  # respect the minimum shot length

        choice = choose_camera(state)
        if choice is not None:
            switcher.cut_to(choice)
