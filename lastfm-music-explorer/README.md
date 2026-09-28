A Django app that uses the [Last.fm API](https://www.last.fm/api) to serve top artists/tracks by country, search suggestions, and genre-based discovery.

## Setup

### 1. Create & activate a virtual environment, then install dependencies

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

### 2. Configure your Last.fm API key

For windows run:
copy .env.example .env

Then open .env and add your key (from https://www.last.fm/api/account/create)

### 3. Run the server

Run:
python manage.py runserver

The app is now live at **http://127.0.0.1:8000/**

## Extra Feature

/api/genre-artists/ - it lets you discover top artists for any genre (e.g. rock, pop, hip-hop). Optionally you can add a country to filter genre results within that country's chart.
