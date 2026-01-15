import streamlit as st
import pandas as pd
import plotly.express as px
from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
import datetime
from utils.pdf_export import generate_summary_pdf
import io

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
        project_df = db.fetch_projects()
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

    st.markdown("---")
    st.subheader("➕ Add / Edit Project")

    # -------------------------
    # Select Project to Edit
    # -------------------------
    proj_options = ["Add New"] + project_df["project_name"].tolist()
    selected_proj = st.selectbox("Select Project", proj_options)

    if selected_proj == "Add New":
        proj_data = {}
    else:
        proj_data = project_df[project_df["project_name"] == selected_proj].iloc[0].to_dict()

    with st.form("project_form", clear_on_submit=True):
        proj_name = st.text_input("Project Name", value=proj_data.get("project_name", ""))
        owner = st.selectbox("Project Owner", emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"],
                             index=0 if not proj_data else emp_df.index[emp_df["Emp_ID"]==proj_data["owner_emp_id"]][0])
        start_date_input = st.date_input("Start Date", value=pd.to_datetime(proj_data.get("start_date", datetime.date.today())).date())
        due_date_input = st.date_input("Due Date", value=pd.to_datetime(proj_data.get("due_date", datetime.date.today() + datetime.timedelta(days=30))).date())
        progress_input = st.slider("Progress (%)", min_value=0, max_value=100, value=int(proj_data.get("progress",0)))
        status_input = st.selectbox("Status", ["Not Started", "In Progress", "Completed"], index=["Not Started","In Progress","Completed"].index(proj_data.get("status","Not Started")))
        submit_btn = st.form_submit_button("Save Project")

        if submit_btn:
            if not proj_name.strip():
                st.error("Project name cannot be empty.")
            else:
                owner_id = int(owner.split(" - ")[0])
                try:
                    db.add_or_update_project({
                        "project_name": proj_name.strip(),
                        "owner_emp_id": owner_id,
                        "status": status_input,
                        "progress": progress_input,
                        "start_date": start_date_input.strftime("%Y-%m-%d"),
                        "due_date": due_date_input.strftime("%Y-%m-%d")
                    })
                    st.success("Project saved successfully.")
                    st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
                    st.experimental_rerun()
                except Exception as e:
                    st.error("Failed to save project.")
                    st.exception(e)

    st.markdown("---")
    st.subheader("📄 Export Project PDF")
    pdf_buffer = io.BytesIO()
    if st.button("Generate PDF"):
        try:
            generate_summary_pdf(
                buffer=pdf_buffer,
                total=len(project_df),
                active=len(project_df[project_df["status"] != "Completed"]),
                resigned=0,
                df=filtered_df,
                title="Project Summary Report"
            )
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="project_summary_report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)
