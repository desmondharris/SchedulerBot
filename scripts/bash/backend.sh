#!/bin/bash
gnome-terminal --window  -- sh -c 'ls; ngrok http --domain=regularly-unbiased-stud.ngrok-free.app 80'
gnome-terminal --window  -- sh -c 'cd /home/altoid/repos/SchedulerBot/apps; sudo python -m http.server 80; exec bash'