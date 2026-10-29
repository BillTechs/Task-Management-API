import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
STATUSES = ["pending", "in_progress", "completed"]
PRIORITIES = ["low", "medium", "high"]

st.set_page_config(page_title="Task Manager", page_icon="✅", layout="wide")
st.title("✅ Task Manager")
st.caption("Streamlit interface connected to the FastAPI backend.")

def api_request(method, path, **kwargs):
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=10, **kwargs)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            st.error(f"API error ({response.status_code}): {detail}")
            return None
        return response.json() if response.content else True
    except requests.RequestException as exc:
        st.error(f"Cannot reach API at {API_URL}. Is the backend running? Details: {exc}")
        return None

with st.sidebar:
    st.subheader("Filter tasks")
    filter_status = st.selectbox("Status", ["all", *STATUSES])
    filter_priority = st.selectbox("Priority", ["all", *PRIORITIES])
    if st.button("Refresh tasks", use_container_width=True):
        st.rerun()
    st.divider()
    st.caption(f"Backend: {API_URL}")

tab_list, tab_create, tab_manage = st.tabs(["Tasks", "Create task", "Update / delete"])

with tab_list:
    params = {}
    if filter_status != "all":
        params["status"] = filter_status
    if filter_priority != "all":
        params["priority"] = filter_priority
    tasks = api_request("GET", "/tasks", params=params)
    if tasks is not None:
        if tasks:
            st.dataframe(tasks, use_container_width=True, hide_index=True)
        else:
            st.info("No tasks match these filters.")
        st.metric("Tasks shown", len(tasks))

with tab_create:
    with st.form("create_task_form", clear_on_submit=True):
        title = st.text_input("Title", max_chars=100)
        description = st.text_area("Description", max_chars=1000)
        priority = st.selectbox("Priority", PRIORITIES, index=1)
        task_status = st.selectbox("Status", STATUSES)
        submitted = st.form_submit_button("Create task", type="primary")
    if submitted:
        if not title.strip():
            st.warning("Title is required.")
        else:
            result = api_request("POST", "/tasks", json={
                "title": title, "description": description,
                "priority": priority, "status": task_status
            })
            if result:
                st.success(f"Created task #{result['id']}")
                st.rerun()

with tab_manage:
    task_id = st.number_input("Task ID", min_value=1, step=1)
    current = api_request("GET", f"/tasks/{int(task_id)}")
    if current:
        st.write(f"**Editing task #{current['id']}: {current['title']}**")
        with st.form("update_task_form"):
            new_title = st.text_input("Title", value=current["title"], max_chars=100)
            new_description = st.text_area("Description", value=current["description"], max_chars=1000)
            new_priority = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(current["priority"]))
            new_status = st.selectbox("Status", STATUSES, index=STATUSES.index(current["status"]))
            update = st.form_submit_button("Save changes", type="primary")
        if update:
            result = api_request("PATCH", f"/tasks/{int(task_id)}", json={
                "title": new_title, "description": new_description,
                "priority": new_priority, "status": new_status
            })
            if result:
                st.success("Task updated.")
                st.rerun()
        if st.button("Delete this task", type="secondary"):
            result = api_request("DELETE", f"/tasks/{int(task_id)}")
            if result:
                st.success("Task deleted.")
                st.rerun()
