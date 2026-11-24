# Campus Management API

Flask API for the Supabase `events`, `registrations`, and `users` tables. Authentication is disabled as requested.

## Run locally

Install dependencies with `pip install -r requirements.txt`, then configure `.env`:

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<publishable-key>
```

Start with `python app.py`. Set `FLASK_DEBUG=true` to enable Flask debug mode during local development.

## Deploy to Render

Create a Render **Web Service** for this repository. Render detects `requirements.txt` and the root `Procfile`; the Procfile launches the app with Gunicorn and binds to Render's `$PORT`. Add `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` under the service's Environment settings. No `.env` file is needed on Render. The health check path can be set to `/`.

## Endpoints

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET | `/api/events` | List events |
| GET | `/api/events/<id>` | Get one event; returns 404 if missing |
| POST | `/api/registrations` | Create a registration; send JSON `{"user_id":"...","event_id":"..."}`; returns 201, or 409 for a duplicate/full/closed event |
| GET | `/api/me/registrations?user_id=<uuid>` | List registrations for the supplied user |
| GET | `/api/events/<id>/registrations` | List registrations and attendee user details for an event |

Errors are returned as JSON with an `error` field. The API expects the database relations shown in `database.png`: `events` has `id`, `organizer_id`, `title`, `capacity`, `status`; `registrations` has `id`, `user_id`, `event_id`, `created_at`; and `users` has `id`, `email`, `role`.

The API uses the configured Supabase key for database access, so the active database policies still apply. Without authentication, clients can supply any `user_id`; do not expose this service to untrusted users until access controls are added. Capacity is checked before insert, so strict capacity enforcement under simultaneous requests should also be implemented transactionally in the database.
