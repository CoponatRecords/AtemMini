"""All tweakable settings in one place.

When a number controls behaviour (an IP address, a port, a timing),
give it a name and keep it here. Then "the switcher moved!" never
requires hunting through 800 lines of code — you change one line in
one file, and every module reads the same value.
"""

# --- ATEM switcher ---------------------------------------------------
ATEM_IP = "192.168.0.240"      # your ATEM Mini's IP address
ATEM_CONNECT_TIMEOUT = 5.0     # seconds to wait for one connection attempt
ATEM_RECONNECT_INTERVAL = 3.0  # seconds between reconnection attempts

# --- Ableton Live (via AbletonOSC) -----------------------------------
OSC_HOST = "127.0.0.1"
OSC_SEND_PORT = 11000          # AbletonOSC listens here
OSC_LISTEN_PORT = 11001        # AbletonOSC sends replies here
METER_POLL_INTERVAL = 0.1      # ask for meter levels 10x per second
TRACK_POLL_INTERVAL = 5.0      # re-ask for the track count (catches a
                               # late-starting Ableton)

# --- Switching brain -------------------------------------------------
NUM_CAMERAS = 4
DECISION_INTERVAL = 10.0       # seconds between switching decisions
METER_WINDOW = 2.0             # judge loudness averaged over this many
                               # seconds, not a single instant
MIN_SHOT_SECONDS = 8.0         # never cut away from a shot faster than this

# --- Persistence -----------------------------------------------------
SETTINGS_FILE = "settings.json"  # thresholds, mappings, active cameras
