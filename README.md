# Intellis

## How to run?
0. These steps work on Python 3.12 (atleast).
1. Create a venv - `python3 -m venv .venv`
2. Source the venv - `source .venv/bin/activate` for Linux and `.venv/Scripts/activate` for Windows.
3. Install dependencies - `pip install -r requirements.txt`
4. Install node.js and run `npm i`
5. Run `python3 manage.py makemigrations` and `python3 manage.py migrate`. 
6. Open 2 terminals. Run `python3 manage.py runserver 0.0.0.0:8000` for running Django in one terminal and run `python3 manage.py tailwind start` for enabling Tailwind with Hot Reload. Access the application on your IP. 
7. For running the CCTVs, please follow the instructions of `RTSP-server`

## Wiki
0. DO NOT NEED TO TOUCH `offset` FOLDER FOR MOST THINGS.
1. Declare your routes in `surakshak/urls.py` and define the routes in `surakshak/views.py`.
2. Use the `surakshak/templates/layout.html` as your HTML layout.
3. Ensure that the docker container is running to host videos via RTSP locally. Please change the `rtsp_url` variable in `surakshak/views` accordingly. Some global hosted RSTP are commented which can be used for testing.
4. Super user creds: `id: offset` and `pass: offset`
5. Add your cameras by going to `/admin` in browser. Camera information is stored in the db.
6. Set `INFERENCE_ENGINE = False` in `settings.py` to disable it.
7. `print()` is not working in some scripts. Use the following snippet for debugging - 
```python
import logging 
logger = logging.getlogger(__name__)
logger.info("YOUR DEBUG MESSAGE")
```     
