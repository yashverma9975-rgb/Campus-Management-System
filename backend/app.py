"""Campus event API backed by the project's Supabase tables."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from postgrest import APIError
from supabase import Client, create_client

load_dotenv()

app = Flask(__name__)


def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be configured")
    return create_client(url, key)


def database():
    try:
        return get_supabase(), None
    except Exception as error:
        app.logger.exception("Supabase client initialization failed")
        return None, (jsonify(error="Database configuration error", details=str(error)), 500)


def db_error(error):
    app.logger.exception("Supabase request failed")
    return jsonify(error="Database request failed", details=getattr(error, "message", str(error))), 500


@app.get("/")
def index():
    return jsonify(name="Campus Management API", endpoints=[
        "GET /api/events", "GET /api/events/<id>", "POST /api/registrations",
        "GET /api/me/registrations?user_id=<uuid>",
        "GET /api/events/<id>/registrations",
    ])


@app.get("/api/events")
def list_events():
    client, error = database()
    if error:
        return error
    try:
        result = client.table("events").select("*").execute()
        return jsonify(result.data)
    except APIError as exc:
        return db_error(exc)


@app.get("/api/events/<event_id>")
def get_event(event_id):
    client, error = database()
    if error:
        return error
    try:
        result = client.table("events").select("*").eq("id", event_id).maybe_single().execute()
        if not result.data:
            return jsonify(error="Event not found"), 404
        return jsonify(result.data)
    except APIError as exc:
        return db_error(exc)


@app.post("/api/registrations")
def create_registration():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Request body must be a JSON object"), 400
    user_id, event_id = payload.get("user_id"), payload.get("event_id")
    if not user_id or not event_id:
        return jsonify(error="user_id and event_id are required"), 400

    client, error = database()
    if error:
        return error
    try:
        event_result = client.table("events").select("id,capacity,status").eq("id", event_id).maybe_single().execute()
        event = event_result.data
        if not event:
            return jsonify(error="Event not found"), 404
        if event.get("status") and str(event["status"]).lower() not in ("open", "active"):
            return jsonify(error="Event is not open for registration"), 409

        existing = client.table("registrations").select("id").eq("user_id", user_id).eq("event_id", event_id).limit(1).execute()
        if existing.data:
            return jsonify(error="User is already registered for this event"), 409

        capacity = event.get("capacity")
        if capacity is not None:
            attendees = client.table("registrations").select("id", count="exact").eq("event_id", event_id).execute()
            if (attendees.count or 0) >= capacity:
                return jsonify(error="Event has reached capacity"), 409

        created = client.table("registrations").insert({"user_id": user_id, "event_id": event_id}).execute()
        return jsonify(created.data[0] if created.data else {}), 201
    except APIError as exc:
        # A unique constraint, if configured in the database, also prevents duplicate registrations.
        if "duplicate" in str(getattr(exc, "message", exc)).lower() or getattr(exc, "code", None) == "23505":
            return jsonify(error="User is already registered for this event"), 409
        return db_error(exc)


@app.get("/api/me/registrations")
def my_registrations():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify(error="user_id query parameter is required (authentication is disabled)"), 400
    client, error = database()
    if error:
        return error
    try:
        result = client.table("registrations").select("*,events(*)").eq("user_id", user_id).execute()
        return jsonify(result.data)
    except APIError as exc:
        return db_error(exc)


@app.get("/api/events/<event_id>/registrations")
def event_registrations(event_id):
    client, error = database()
    if error:
        return error
    try:
        event = client.table("events").select("id").eq("id", event_id).maybe_single().execute()
        if not event.data:
            return jsonify(error="Event not found"), 404
        result = client.table("registrations").select("*,users(id,email,role)").eq("event_id", event_id).execute()
        return jsonify(result.data)
    except APIError as exc:
        return db_error(exc)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
