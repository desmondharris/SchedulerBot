#!/bin/bash
gnome-terminal --window  -- sh -c 'ls; ngrok http --domain=regularly-unbiased-stud.ngrok-free.app 80'
gnome-terminal --window  -- sh -c 'python -m http.server 80'