# pages/10_Projects.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
import datetime

def show():
    # -------------------------
    # Login & Role
    # -------------------------
    require_login()
    show_role_badge()
    logout_user()

    st.title("📈 Project Health Tracker")

    # -------------------------
    # Load Project Data
    # -------------------------
    try:
        project_df = db.fetch_projects()  # columns: project_id, project_name, owner_emp_id, status, progress, start_date, due_date
        emp_df = db.fetch_employees()
    except Exception as e:
        st.error("Failed to load projects or employee data.")
        st.exception(e)
        return

    if project_df.empty:
        st.info("No project data available.")
        return

    # Map owner names
    emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()
    project_df["Owner"] = project_df["owner_emp_id"].map(emp_map).fillna(project_df["owner_emp_id"].astype(str))

    # -------------------------
    # Filters
    # -------------------------
    st.sidebar.header("Filters")
    status_filter = st.sidebar.selectbox("Project Status", ["All"] + sorted(project_df["status"].unique()))
    owner_filter = st.sidebar.selectbox("Project Owner", ["All"] + sorted(project_df["Owner"].unique()))
    date_range = st.sidebar.date_input("End Before Date", value=datetime.date.today())

    filtered_df = project_df.copy()
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["status"] == status_filter]
    if owner_filter != "All":
        filtered_df = filtered_df[filtered_df["Owner"] == owner_filter]
    filtered_df = filtered_df[pd.to_datetime(filtered_df["due_date"]) <= pd.to_datetime(date_range)]

    st.subheader("🗂️ Projects Overview")
    st.dataframe(
        filtered_df[["project_id", "project_name", "Owner", "status", "progress", "start_date", "due_date"]],
        height=400
    )

    # -------------------------
    # Project Progress Analytics
    # -------------------------
    st.subheader("📊 Project Completion Analytics")
    if not filtered_df.empty:
        fig = px.bar(
            filtered_df,
            x="project_name",
            y="progress",
            color="status",
            text="progress",
            title="Project Progress (%)",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)

    # -------------------------
    # Add / Update Project
    # -------------------------
    st.markdown("---")
    st.subheader("➕ Add / Update Project")
    with st.form("project_form", clear_on_submit=True):
        proj_name = st.text_input("Project Name")
        owner = st.selectbox("Project Owner", emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"])
        start_date_input = st.date_input("Start Date", value=datetime.date.today())
        due_date_input = st.date_input("Due Date", value=datetime.date.today() + datetime.timedelta(days=30))
        progress_input = st.slider("Progress (%)", min_value=0, max_value=100, value=0)
        status_input = st.selectbox("Status", ["Not Started", "In Progress", "Completed"])
        submit_btn = st.form_submit_button("Save Project")

        if submit_btn:
            owner_id = int(owner.split(" - ")[0])
            try:
                db.add_or_update_project({
                    "project_name": proj_name,
                    "owner_emp_id": owner_id,
                    "status": status_input,
                    "progress": progress_input,
                    "start_date": start_date_input.strftime("%Y-%m-%d"),
                    "due_date": due_date_input.strftime("%Y-%m-%d")
                })
                st.success("Project saved successfully.")
                st.experimental_rerun()
            except Exception as e:
                st.error("Failed to save project.")
                st.exception(e)
