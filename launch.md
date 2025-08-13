# Surakshak Deployment Guide

## How to run?
0. These steps work on Python 3.12 (atleast).
1. Create a venv - `python3 -m venv .venv`
2. Source the venv - `source .venv/bin/activate` for Linux and `.venv/Scripts/activate` for Windows.
3. Install dependencies - `pip install -r requirements.txt`
4. Install node.js and run `npm i`
5. Run `python3 manage.py makemigrations` and `python3 manage.py migrate`. 
6. Open 2 terminals. Run `python3 manage.py runserver 0.0.0.0:8000` for running Django in one terminal and run `python3 manage.py tailwind start` for enabling Tailwind with Hot Reload. Access the application on your IP.
7. Get the RTSP urls for all connected cameras (the process of getting these url might slightly vary depending on the choice of DVL and type of camera but quick google search and an easy guide should work)
8. On the web interface, go to settings and add camera RTSP url and it should start working! (restart the application once more if not camera feed doesn't turn up)

