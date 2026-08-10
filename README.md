# Aperture Control — audio-driven ATEM Mini camera switcher

Listens to your Ableton Live tracks and automatically cuts an ATEM
Mini to the camera(s) that match whoever is playing. Drums loud →
drummer cam. Everything below its threshold → nothing changes.

## How it works

```
Ableton Live ──OSC──▶ AppState ──▶ brain ──▶ Switcher ──▶ ATEM Mini
 (AbletonOSC)            │                      │
                         └──▶ gui_queue ◀───────┘
                                 │
                                GUI
```

* **[ableton.py](ableton.py)** polls every track's output meter 10×/s
  through [AbletonOSC](https://github.com/ideoforms/AbletonOSC) and
  keeps `AppState` fresh.
* **[state.py](state.py)** is the single source of truth all threads
  share (one object, one lock). Your settings persist in
  `settings.json`.
* **[brain.py](brain.py)** decides every 10 s: tracks louder (on
  average) than their threshold vote for their mapped cameras; one
  vote wins at random. Never re-cuts to the shot already on air,
  never abandons a shot before `MIN_SHOT_SECONDS`.
* **[atem.py](atem.py)** owns the ATEM connection and reconnects by
  itself if the link drops mid-show.
* **[gui.py](gui.py)** is the window. Only the main thread touches
  Tk; other threads talk to it through a queue.
* **[config.py](config.py)** holds every tweakable value — the ATEM's
  IP lives there.

## Setup

1. Install [AbletonOSC](https://github.com/ideoforms/AbletonOSC) as a
   Remote Script in Ableton Live (it listens on port 11000).
2. `pip install -r requirements.txt`
3. Set your ATEM's IP in `config.py`.
4. `python main.py` — Ableton may be started before *or* after; the
   track rows appear as soon as it answers.

## Using it

* **Left-click** a camera button: cut to that camera now.
* **Right-click** a camera button: allow/forbid it for the
  auto-switcher (gray = the brain will never pick it).
* **Play/stop button**: automation on/off.
* Per track: drag the **white thumb** to set the loudness threshold
  (bar turns green when the track is above it), tick **1–4** to map
  the track to cameras.

Thresholds, mappings and camera choices are remembered across
restarts (`settings.json`).

## For the curious: the 2026 refactor

This codebase was restructured commit by commit — each commit message
explains one reliability lesson learned the hard way (threads talking
through text files, Tkinter and thread safety, connections that must
survive a live show, why the app used to kill other processes on
startup, …). `git log` is the guided tour.
