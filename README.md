# EcoBuddy

A sustainability-focused social platform where users share eco-friendly tips, connect with like-minded peers, and build greener communities.

**Live demo:** [sustainability-app-b15-88368bb3ea4a.herokuapp.com](https://sustainability-app-b15-88368bb3ea4a.herokuapp.com/)

## Features

- **Social feed** — Browse and create posts tagged by sustainability topics (recycling, transport, campus life, food, and more)
- **User profiles** — Custom bios, profile pictures, topic preferences, and achievement badges
- **Friends system** — Send/accept friend requests, friends-only posts, and user search
- **Direct messaging** — Real-time chat between users
- **Drafts** — Save posts as drafts and publish when ready
- **Notifications** — In-app alerts for likes, friend requests, messages, and moderation actions
- **Content moderation** — Flag posts/messages/profiles; moderators can review, remove content, and suspend users
- **Role-based access** — User, moderator, and admin roles with a dedicated moderation dashboard
- **Google OAuth** — Optional sign-in with Google (email/password signup also supported)

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python, Django 5.2 |
| Auth | django-allauth (email + Google OAuth) |
| Database | SQLite (local) / PostgreSQL (production) |
| File storage | Local filesystem (local) / AWS S3 (production) |
| Deployment | Heroku, Gunicorn, WhiteNoise |

## Local Setup

### Prerequisites

- Python 3.11+
- pip

### 1. Clone and install

```bash
git clone <your-repo-url>
cd EcoBuddy

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

Copy the example env file and adjust as needed:

```bash
cp .env.example .env
```

For a quick local demo, the defaults work out of the box — no AWS or Google credentials required. Uploaded images are stored in `./media/`.

### 3. Initialize the database

```bash
python manage.py migrate
python manage.py seed_demo
```

The `seed_demo` command creates two accounts you can use immediately:

| Username | Password | Role |
|----------|----------|------|
| `demo` | `demo1234` | User (with sample posts) |
| `moderator` | `demo1234` | Moderator |

To create your own admin account, sign up with an email listed in `ADMIN_EMAILS` inside `.env`, or run:

```bash
python manage.py createsuperuser
```

Then promote the user to admin via the Django admin panel (`/admin/`) or the in-app admin page.

### 4. Run the dev server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Optional: Google OAuth

1. Create a Google Cloud OAuth 2.0 client ID (Web application type).
2. Add `http://127.0.0.1:8000/accounts/google/login/callback/` as an authorized redirect URI.
3. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your `.env` file.
4. In the [Django admin Sites framework](http://127.0.0.1:8000/admin/sites/site/), confirm the site domain matches your local URL (`127.0.0.1:8000`).

## Project Structure

```
EcoBuddy/
├── sustainability_project/   # Django project settings & URLs
├── user_dashboard/           # Feed, posts, friends, moderation, notifications
├── user_info/                # Extended user profile data
├── messaging/                # Direct messaging & chat rooms
├── templates/                # Auth templates (login, signup)
├── staticfiles/              # Collected static assets (CSS)
├── manage.py
├── requirements.txt
├── Procfile                  # Heroku deployment config
└── .env.example
```

## Production Deployment

The app is configured for Heroku out of the box. Set these environment variables on your hosting platform:

- `SECRET_KEY`
- `DATABASE_URL`
- `HEROKU=1`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME` (for media uploads)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (for Google login)

Migrations run automatically via the `release` phase in the `Procfile`.

## Security Note

If this repository was ever public with hardcoded credentials, rotate your AWS keys and Google OAuth secrets before deploying. All secrets are now loaded from environment variables — see `.env.example` for the full list.
