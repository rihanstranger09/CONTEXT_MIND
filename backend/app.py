"""Small task API used to demonstrate a deployable Flask microservice."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request


def database_url() -> str:
    """Build a libpq URL from environment variables (or accept DATABASE_URL)."""
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return configured_url
    return "postgresql://{user}:{password}@{host}:{port}/{name}".format(
        user=os.getenv("POSTGRES_USER", "appuser"),
        password=os.getenv("POSTGRES_PASSWORD", "appsecret"),
        host=os.getenv("POSTGRES_HOST", "db"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        name=os.getenv("POSTGRES_DB", "tasks"),
    )


def get_connection():
    return psycopg2.connect(database_url(), connect_timeout=3)


def initialize_database(retries: int = 10, delay: float = 2.0) -> None:
    """Create the tiny schema, retrying while the database becomes available."""
    for attempt in range(retries):
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """CREATE TABLE IF NOT EXISTS tasks (
                            id SERIAL PRIMARY KEY,
                            title VARCHAR(200) NOT NULL,
                            description TEXT NOT NULL DEFAULT '',
                            completed BOOLEAN NOT NULL DEFAULT FALSE,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )"""
                    )
            return
        except psycopg2.OperationalError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)


def create_app(initialize: bool = True) -> Flask:
    app = Flask(__name__)
    if initialize:
        initialize_database()

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="task-api")

    @app.get("/ready")
    def ready():
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
            return jsonify(status="ready", database="connected")
        except psycopg2.Error:
            return jsonify(status="not_ready", database="unavailable"), 503

    @app.get("/api/tasks")
    def list_tasks():
        with get_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM tasks ORDER BY id DESC")
                rows = cursor.fetchall()
        return jsonify([_serialize(row) for row in rows])

    @app.post("/api/tasks")
    def add_task():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Request body must be a JSON object."), 400
        title = data.get("title")
        description = data.get("description", "")
        if not isinstance(title, str) or not title.strip():
            return jsonify(error="title is required and must be a non-empty string."), 400
        if len(title.strip()) > 200:
            return jsonify(error="title must be 200 characters or fewer."), 400
        if not isinstance(description, str):
            return jsonify(error="description must be a string."), 400
        with get_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "INSERT INTO tasks (title, description) VALUES (%s, %s) RETURNING *",
                    (title.strip(), description.strip()),
                )
                row = cursor.fetchone()
        return jsonify(_serialize(row)), 201

    @app.patch("/api/tasks/<int:task_id>")
    def update_task(task_id: int):
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get("completed"), bool):
            return jsonify(error="completed must be provided as a boolean."), 400
        with get_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "UPDATE tasks SET completed = %s WHERE id = %s RETURNING *",
                    (data["completed"], task_id),
                )
                row = cursor.fetchone()
        if row is None:
            return jsonify(error="Task not found."), 404
        return jsonify(_serialize(row))

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id: int):
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
                deleted = cursor.rowcount
        if not deleted:
            return jsonify(error="Task not found."), 404
        return "", 204

    return app


def _serialize(row: dict) -> dict:
    result = dict(row)
    if isinstance(result.get("created_at"), datetime):
        result["created_at"] = result["created_at"].astimezone(timezone.utc).isoformat()
    return result


app = create_app(initialize=os.getenv("SKIP_DB_INIT", "false").lower() != "true")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
