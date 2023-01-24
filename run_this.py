
'''  Doesn't work atm '''
from pythonosc import dispatchers
from pythonosc import osc_server
from pythonosc import udp_client
import threading
import time
import logging
import time
import PyATEMMax
import random
import concurrent.futures
import subprocess



def script1():
    exec(open("main.py").read())

def script2():
    exec(open("Instrument_Level.py").read())

# Use a ThreadPoolExecutor to run script1 and script2 concurrently
with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.submit(script1)
    executor.submit(script2)

