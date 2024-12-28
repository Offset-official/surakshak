# Intellis

## How to run?
1. Create a venv - `python3 -m venv .venv` 
2. Source the venv - `source .venv/bin/activate` for Linux and `.venv/Scripts/activate` for Windows.
3. Install dependencies - `pip install -r requirements.txt`
4. Install node.js and run `npm i`
5. Open 2 terminals. Run `python3 manage.py runserver` for running Django in one terminal and run `python manage.py tailwind start` for enabling Tailwind with Hot Reload.

## Wiki
1. Declare your routes in `offset/urls.py` and define the routes in `offset/surakshak/views.py`. 
2. Use the `surakshak/templates/layout.html` as your HTML layout.
