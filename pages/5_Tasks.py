# pages/5_Tasks.py
"""
Task Management — Workforce Intelligence System
Assign, edit, delete, and analyze tasks.
"""

import streamlit as st
import pandas as pd
import datetime
from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db

def show():
    # -----------------------
    # Login & Role Check
    # -----------------------
    require_login()
    show_role_badge()
    logout_user()

    role = st.session_state.get("role", "Employee")
    username = st.session_state.get("user", "unknown")

    st.title("🗂️ Task Management")

    # -----------------------
    # Load Data Safely
    # -----------------------
    try:
        emp_df = db.fetch_employees()
        emp_df = emp_df[emp_df["Status"]=="Active"]  # Only active employees
    except Exception:
        emp_df = pd.DataFrame(columns=["Emp_ID", "Name", "Status"])

    try:
        tasks_df = db.fetch_tasks()
    except Exception:
        tasks_df = pd.DataFrame(columns=["task_id","task_name","emp_id","assigned_by","due_date","priority","status","remarks"])

    if emp_df.empty:
        st.info("No active employees available.")
    if tasks_df.empty:
        st.info("No tasks available.")

    emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict() if not emp_df.empty else {}

    # -----------------------
    # Assign Task (Admin/Manager)
    # -----------------------
    if role in ["Admin", "Manager"]:
        st.subheader("➕ Assign Task")
        if not emp_df.empty:
            with st.form("assign_task", clear_on_submit=True):
                task_title = st.text_input("Task Title")
                assignee = st.selectbox(
                    "Assign to",
                    (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist()
                )
                due_date = st.date_input("Due Date", value=datetime.date.today())
                priority = st.selectbox("Priority", ["Low","Medium","High"])
                remarks = st.text_area("Remarks")
                submit = st.form_submit_button("Assign Task")

                if submit:
                    if not task_title.strip():
                        st.error("Task title is required.")
                    else:
                        emp_id = int(assignee.split(" - ")[0])
                        try:
                            db.add_task({
                                "task_name": task_title.strip(),
                                "emp_id": emp_id,
                                "assigned_by": username,
                                "due_date": due_date.strftime("%Y-%m-%d"),
                                "priority": priority,
                                "status": "Pending",
                                "remarks": remarks or ""
                            })
                            tasks_df = db.fetch_tasks()  # ✅ Safe refresh
                            st.success("✅ Task assigned successfully.")
                        except Exception as e:
                            st.error("❌ Failed to assign task.")
                            st.exception(e)
        else:
            st.info("No active employees available to assign tasks.")

    st.markdown("---")

    # -----------------------
    # Search & Filter Tasks
    # -----------------------
    st.subheader("🔎 Search / Filter Tasks")
    search_text = st.text_input("Search (title, assignee, remarks)").lower().strip()
    filter_status = st.selectbox("Status Filter", ["All", "Pending", "In-Progress", "Completed"])
    filter_priority = st.selectbox("Priority Filter", ["All", "Low", "Medium", "High"])

    tasks_display = tasks_df.copy()
    if not tasks_display.empty:
        tasks_display["Employee"] = tasks_display["emp_id"].map(emp_map).fillna(tasks_display["emp_id"].astype(str))

        if search_text:
            mask = (
                tasks_display["task_name"].str.lower().str.contains(search_text, na=False) |
                tasks_display["Employee"].str.lower().str.contains(search_text, na=False) |
                tasks_display["remarks"].str.lower().str.contains(search_text, na=False)
            )
            tasks_display = tasks_display[mask]

        if filter_status != "All":
            tasks_display = tasks_display[tasks_display["status"] == filter_status]

        if filter_priority != "All":
            tasks_display = tasks_display[tasks_display["priority"] == filter_priority]

    st.dataframe(
        tasks_display[["task_id","task_name","Employee","assigned_by","due_date","priority","status","remarks"]] 
        if not tasks_display.empty else pd.DataFrame(columns=["task_id","task_name","Employee","assigned_by","due_date","priority","status","remarks"]),
        height=300
    )

    st.markdown("---")

    # -----------------------
    # Edit / Update / Delete Task (Admin/Manager)
    # -----------------------
    if role in ["Admin", "Manager"] and not tasks_display.empty:
        st.subheader("✏️ Edit / Delete Task")
        task_ids = tasks_display["task_id"].astype(str).tolist()
        sel_task = st.selectbox("Select Task ID", task_ids)

        if sel_task:
            task_row = tasks_display[tasks_display["task_id"] == int(sel_task)].iloc[0].to_dict()
            with st.form("edit_task"):
                e_title = st.text_input("Task Title", value=task_row.get("task_name",""))
                e_assignee = st.selectbox(
                    "Assign To",
                    (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist(),
                    index=0
                )
                e_due = st.date_input(
                    "Due Date",
                    value=pd.to_datetime(task_row.get("due_date", datetime.date.today())).date()
                )
                e_priority = st.selectbox("Priority", ["Low","Medium","High"], index=["Low","Medium","High"].index(task_row.get("priority","Low")))
                e_status = st.selectbox("Status", ["Pending","In-Progress","Completed"], index=["Pending","In-Progress","Completed"].index(task_row.get("status","Pending")))
                e_remarks = st.text_area("Remarks", value=task_row.get("remarks",""))

                update_btn = st.form_submit_button("Save Changes")
                delete_btn = st.form_submit_button("Delete Task")

                if update_btn:
                    try:
                        emp_id_new = int(e_assignee.split(" - ")[0])
                        db.update_task(int(sel_task), {
                            "task_name": e_title.strip(),
                            "emp_id": emp_id_new,
                            "due_date": e_due.strftime("%Y-%m-%d"),
                            "priority": e_priority,
                            "status": e_status,
                            "remarks": e_remarks
                        })
                        tasks_df = db.fetch_tasks()  # ✅ Safe refresh
                        st.success("✅ Task updated successfully.")
                    except Exception as e:
                        st.error("❌ Failed to update task.")
                        st.exception(e)

                elif delete_btn:
                    try:
                        db.delete_task(int(sel_task))
                        tasks_df = db.fetch_tasks()  # ✅ Safe refresh
                        st.success("✅ Task deleted successfully.")
                    except Exception as e:
                        st.error("❌ Failed to delete task.")
                        st.exception(e)

    st.markdown("---")

    # -----------------------
    # Task Completion Analytics
    # -----------------------
    st.subheader("📊 Task Completion Analytics")
    if not tasks_df.empty:
        status_counts = tasks_df["status"].value_counts()
        st.bar_chart(status_counts)
    else:
        st.info("No task data to display analytics.")
