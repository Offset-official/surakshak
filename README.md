# Intellis

## How to run?
1. Create a venv - `python3 -m venv .venv`
2. Source the venv - `source .venv/bin/activate` for Linux and `something similar` for Windows.
3. Install dependencies - `pip install -r requirements.txt`
4. Install node.js and run `npm i`
5. Open 2 terminals. Run `python manage.py runserver` for running Django in one terminal and run `npm run watch:css` for enabling Tailwind in another.

## Wiki
1. Declare your routes in `offset/urls.py` and define the routes in `offset/views.py`. 
2. Use the `templates/_base.html` as your HTML layout.

### Problems
1. Hot reload couldn't be set up. You'll have to refresh the website after making any changes.