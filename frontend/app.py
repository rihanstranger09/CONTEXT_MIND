"""Streamlit web client for the task-api service."""
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:5000").rstrip("/")

st.set_page_config(page_title="Task Board | Scalable App", page_icon="📋", layout="wide")
st.title("📋 Scalable Task Board")
st.caption("A Streamlit frontend backed by a Flask API and PostgreSQL database.")


def api_request(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=5, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None, None
    except requests.RequestException as error:
        detail = error.response.text if error.response is not None else str(error)
        return None, detail


with st.form("new-task", clear_on_submit=True):
    st.subheader("Add a task")
    title = st.text_input("Title", max_chars=200, placeholder="e.g. Deploy the API")
    description = st.text_area("Description", placeholder="Optional details")
    submitted = st.form_submit_button("Create task", type="primary")
    if submitted:
        if not title.strip():
            st.warning("Enter a title before creating a task.")
        else:
            _, error = api_request("POST", "/api/tasks", json={"title": title, "description": description})
            if error:
                st.error(f"Could not create task: {error}")
            else:
                st.success("Task created.")
                st.rerun()

st.divider()
left, right = st.columns([3, 1])
left.subheader("Tasks")
if right.button("↻ Refresh", use_container_width=True):
    st.rerun()

tasks, error = api_request("GET", "/api/tasks")
if error:
    st.error(f"The backend is unavailable at {API_URL}. Details: {error}")
    st.info("Check that the backend and database containers are healthy.")
elif not tasks:
    st.info("No tasks yet. Add one above to get started.")
else:
    for task in tasks:
        with st.container(border=True):
            col1, col2, col3 = st.columns([0.5, 5, 1])
            completed = col1.checkbox("Complete", value=task["completed"], key=f"done-{task['id']}", label_visibility="collapsed")
            if completed != task["completed"]:
                _, update_error = api_request("PATCH", f"/api/tasks/{task['id']}", json={"completed": completed})
                if update_error:
                    st.error(f"Could not update task: {update_error}")
                else:
                    st.rerun()
            label = f"~~{task['title']}~~" if task["completed"] else f"**{task['title']}**"
            col2.markdown(label)
            if task["description"]:
                col2.caption(task["description"])
            if col3.button("Delete", key=f"delete-{task['id']}"):
                _, delete_error = api_request("DELETE", f"/api/tasks/{task['id']}")
                if delete_error:
                    st.error(f"Could not delete task: {delete_error}")
                else:
                    st.rerun()

st.caption(f"API endpoint: `{API_URL}`")
