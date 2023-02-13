
To run this script, just run the script  main.py

This script writes instrument_status.txt, piano_status.txt, drum_status.txt, voice_status.txt files with a value representing the current audio level of the tracks.

It then uses the values stored to switch cameras automatically.

The ATEM mini has to be on and connected through ethernet. Check the connection status with the "Atem Setup" app.
The ATEM mini's IP adress has to be set to 192.168.0.124

Ableton needs to have AbletonOSC installed : https://github.com/ideoforms/AbletonOSC
AbletonOSC also has to be set in as a midi controller in ableton's Link/Tempo/Midi settings' tab


This works with an envelope follower (Max4Live) linked to a utility's gain on the third (group all instrument) and fourth (piano with a vst) tracks of ableton

We used threading to run the processes in parallel.