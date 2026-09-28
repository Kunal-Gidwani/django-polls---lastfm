# Django Polls

A Django polls app where users vote on public polls and each admin only sees their own questions plus vote analytics (counts and share %).

# 1. Setup

python -m venv .venv
.venv\Scripts\activate  
pip install -r requirements.txt

# 2. Apply migrations

python manage.py migrate

# 3. As an admin

## Create your admin account (username must be exactly 5 characters)

python manage.py createsuperuser

## Run the server

python manage.py runserver 8001

Open http://127.0.0.1:8001/admin/

- Add a poll: Admin → Questions → Add Question → fill question + choices → Save

# 4. As a user

python manage.py runserver 8001

Open http://127.0.0.1:8001/polls/

- Click a poll → select an option → Vote

# Analytics

Each admin who creates a question can view its vote analytics (choice, count, share %). Admins only see their own questions.

- Log in at /admin/
- Click Analytics in the left sidebar (under Polls)
