# pages/4_Reports.py
"""
Workforce Reports — FIXED
- All graphs captured as PNG and embedded in PDF
- Plotly charts with hover for screen
- Matplotlib for PDF export
- Clean layout
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import io

from utils import database as db
from utils.auth import require_login, show_role_badge, logout_user
from utils.pdf_export import generate_master_report
from utils.analytics import department_distribution, gender_ratio, average_salary_by_dept

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")

require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")

if role not in ["Admin", "Manager", "HR"]:
    st.warning("⚠️ Access denied. Admin / Manager / HR only.")
    st.stop()

st.title("📊 Workforce Reports")

# -------------------------
# Load data safely
# -------------------------
def safe_fetch(func):
    try:
        return func()
    except Exception:
        return pd.DataFrame()

df_employees = safe_fetch(db.fetch_employees)
df_mood      = safe_fetch(db.fetch_mood_logs)
df_attendance = safe_fetch(db.fetch_attendance)
df_projects  = safe_fetch(db.fetch_projects)

# -------------------------
# Sidebar Filters
# -------------------------
st.sidebar.header("🔍 Filters")

dept_options = ["All"] + sorted(df_employees["Department"].dropna().unique().tolist()) if not df_employees.empty else ["All"]
status_options = ["All"] + sorted(df_employees["Status"].dropna().unique().tolist()) if not df_employees.empty else ["All"]

dept_filter   = st.sidebar.selectbox("Department", dept_options)
status_filter = st.sidebar.selectbox("Status", status_options)

filtered_df = df_employees.copy()
if dept_filter != "All":
    filtered_df = filtered_df[filtered_df["Department"] == dept_filter]
if status_filter != "All":
    filtered_df = filtered_df[filtered_df["Status"] == status_filter]

# -------------------------
# Summary Metrics
# -------------------------
st.subheader("📌 Summary")

total_emp    = len(filtered_df)
active_emp   = len(filtered_df[filtered_df["Status"] == "Active"])   if "Status" in filtered_df.columns else 0
resigned_emp = len(filtered_df[filtered_df["Status"] == "Resigned"]) if "Status" in filtered_df.columns else 0
dept_count   = filtered_df["Department"].nunique() if not filtered_df.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("👥 Total Employees",  total_emp)
c2.metric("✅ Active",           active_emp)
c3.metric("🚪 Resigned",         resigned_emp)
c4.metric("🏢 Departments",      dept_count)

st.divider()

# ===========================
# Helper: save matplotlib fig to PNG bytes
# ===========================
def fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    data = buf.read()
    plt.close(fig)
    return data

# Storage for PDF figures
pdf_figs = {}

# -------------------------
# 1. Department Distribution
# -------------------------
st.subheader("🏢 Department-wise Distribution")

if not filtered_df.empty and "Department" in filtered_df.columns:
    dept_counts = department_distribution(filtered_df)

    # Plotly (screen)
    fig_d = go.Figure(go.Bar(
        x=dept_counts.index.tolist(),
        y=dept_counts.values.tolist(),
        text=dept_counts.values.tolist(),
        textposition="outside",
        marker_color="#667eea",
        hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>"
    ))
    fig_d.update_layout(
        xaxis_title="Department", yaxis_title="Count",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=380
    )
    st.plotly_chart(fig_d, use_container_width=True)

    # Matplotlib (PDF)
    fig_m, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(dept_counts.index, dept_counts.values, color="#667eea")
    ax.set_title("Employees per Department"); ax.set_ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    pdf_figs["dept"] = fig_to_png(fig_m)
else:
    st.info("No data for department chart.")

# -------------------------
# 2. Gender Distribution
# -------------------------
st.subheader("👥 Gender Distribution")

if not filtered_df.empty and "Gender" in filtered_df.columns:
    gender_counts = gender_ratio(filtered_df)
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig_g = go.Figure(go.Pie(
            labels=gender_counts.index.tolist(),
            values=gender_counts.values.tolist(),
            hole=0.4,
            hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
            marker=dict(colors=["#667eea", "#f472b6"])
        ))
        fig_g.update_layout(title="Gender Ratio", height=340, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_g, use_container_width=True)

    with col_g2:
        g_dept = filtered_df.groupby(["Department", "Gender"]).size().reset_index(name="Count")
        fig_gd = px.bar(g_dept, x="Department", y="Count", color="Gender",
                        barmode="group", title="Gender by Department",
                        color_discrete_map={"Male": "#667eea", "Female": "#f472b6"})
        fig_gd.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=340)
        st.plotly_chart(fig_gd, use_container_width=True)

    # Matplotlib for PDF
    fig_m, ax = plt.subplots(figsize=(5, 4))
    ax.pie(gender_counts.values, labels=gender_counts.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("Gender Distribution"); ax.axis("equal")
    plt.tight_layout()
    pdf_figs["gender"] = fig_to_png(fig_m)
else:
    st.info("No gender data available.")

# -------------------------
# 3. Average Salary
# -------------------------
st.subheader("💰 Average Salary by Department")

if not filtered_df.empty and "Salary" in filtered_df.columns:
    avg_salary = average_salary_by_dept(filtered_df)

    fig_s = go.Figure(go.Bar(
        x=avg_salary.index.tolist(),
        y=avg_salary.values.tolist(),
        text=[f"₹{int(v):,}" for v in avg_salary.values],
        textposition="outside",
        marker=dict(color=avg_salary.values.tolist(), colorscale="Oranges"),
        hovertemplate="<b>%{x}</b><br>Avg: ₹%{y:,.0f}<extra></extra>"
    ))
    fig_s.update_layout(
        xaxis_title="Department", yaxis_title="Avg Salary",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=380
    )
    st.plotly_chart(fig_s, use_container_width=True)

    # Matplotlib for PDF
    fig_m, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(avg_salary.index, avg_salary.values, color="#f97316")
    ax.set_title("Average Salary by Department"); ax.set_ylabel("Salary")
    plt.xticks(rotation=45, ha="right")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"{int(bar.get_height())}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    pdf_figs["salary"] = fig_to_png(fig_m)
else:
    st.info("No salary data available.")

# -------------------------
# 4. Mood Report
# -------------------------
st.subheader("😊 Mood Report")

if not df_mood.empty and "remarks" in df_mood.columns:
    mood_counts = df_mood["remarks"].str.extract(r"(Happy|Neutral|Stressed)")[0].value_counts()

    if not mood_counts.empty:
        mood_color = {"Happy": "#22c55e", "Neutral": "#f59e0b", "Stressed": "#ef4444"}
        colors = [mood_color.get(m, "#667eea") for m in mood_counts.index]

        fig_mood = go.Figure(go.Bar(
            x=mood_counts.index.tolist(),
            y=mood_counts.values.tolist(),
            text=mood_counts.values.tolist(),
            textposition="outside",
            marker_color=colors,
            hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>"
        ))
        fig_mood.update_layout(
            title="Mood Distribution",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=350
        )
        st.plotly_chart(fig_mood, use_container_width=True)

        # Matplotlib for PDF
        fig_m, ax = plt.subplots(figsize=(7, 4))
        bars = ax.bar(mood_counts.index, mood_counts.values, color=colors)
        ax.set_title("Mood Distribution"); ax.set_ylabel("Count")
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
        plt.tight_layout()
        pdf_figs["mood"] = fig_to_png(fig_m)
    else:
        st.info("No mood breakdown available.")
else:
    st.info("No mood data available.")

# -------------------------
# 5. Project Report
# -------------------------
st.subheader("📈 Project Health Report")

if not df_projects.empty and "status" in df_projects.columns:
    proj_status = df_projects["status"].value_counts()

    proj_colors = {"Active": "#667eea", "Completed": "#22c55e",
                   "On Hold": "#f59e0b", "Cancelled": "#ef4444"}
    bar_colors = [proj_colors.get(s, "#94a3b8") for s in proj_status.index]

    fig_proj = go.Figure(go.Bar(
        x=proj_status.index.tolist(),
        y=proj_status.values.tolist(),
        text=proj_status.values.tolist(),
        textposition="outside",
        marker_color=bar_colors,
        hovertemplate="<b>%{x}</b><br>Projects: %{y}<extra></extra>"
    ))
    fig_proj.update_layout(
        title="Projects by Status",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=350
    )
    st.plotly_chart(fig_proj, use_container_width=True)

    # Progress distribution
    if "progress" in df_projects.columns:
        st.subheader("📊 Project Progress Distribution")
        fig_prog = px.histogram(
            df_projects, x="progress", nbins=10,
            title="Project Progress Distribution (%)",
            labels={"progress": "Progress (%)"},
            color_discrete_sequence=["#667eea"]
        )
        fig_prog.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=320
        )
        st.plotly_chart(fig_prog, use_container_width=True)

    # Matplotlib for PDF
    fig_m, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(proj_status.index, proj_status.values, color=bar_colors)
    ax.set_title("Projects by Status"); ax.set_ylabel("Count")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    pdf_figs["project"] = fig_to_png(fig_m)
else:
    st.info("No project data available.")

# -------------------------
# 6. Attendance Summary
# -------------------------
st.subheader("📋 Attendance Summary")

if not df_attendance.empty and "status" in df_attendance.columns:
    att_counts = df_attendance["status"].value_counts()

    att_color = {"Present": "#22c55e", "Absent": "#ef4444",
                 "Half-day": "#f59e0b", "Remote": "#667eea"}
    att_bar_colors = [att_color.get(s, "#94a3b8") for s in att_counts.index]

    fig_att = go.Figure(go.Bar(
        x=att_counts.index.tolist(),
        y=att_counts.values.tolist(),
        text=att_counts.values.tolist(),
        textposition="outside",
        marker_color=att_bar_colors,
        hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>"
    ))
    fig_att.update_layout(
        title="Attendance Status Distribution",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=350
    )
    st.plotly_chart(fig_att, use_container_width=True)

    # Matplotlib for PDF
    fig_m, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(att_counts.index, att_counts.values, color=att_bar_colors)
    ax.set_title("Attendance Distribution"); ax.set_ylabel("Count")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    pdf_figs["attendance"] = fig_to_png(fig_m)
else:
    st.info("No attendance data available.")

# -------------------------
# Export Master PDF  ← FIXED: graphs now captured and embedded
# -------------------------
st.divider()
st.subheader("📄 Download Master Workforce PDF")

if st.button("🖨️ Generate PDF Report"):
    pdf_buffer = io.BytesIO()
    try:
        generate_master_report(
            buffer=pdf_buffer,
            employees_df=filtered_df,
            attendance_df=df_attendance,
            mood_df=df_mood,
            projects_df=df_projects,
            notifications_df=pd.DataFrame(),
            dashboard_fig=pdf_figs.get("dept"),        # dept chart as dashboard fig
            attendance_fig=pdf_figs.get("attendance"),
            mood_fig=pdf_figs.get("mood"),
            project_fig=pdf_figs.get("project"),
        )
        pdf_buffer.seek(0)
        st.download_button(
            "⬇️ Download PDF",
            pdf_buffer,
            "workforce_report.pdf",
            "application/pdf"
        )
        st.success("✅ PDF ready! Click above to download.")
    except Exception as e:
        st.error("Failed to generate PDF.")
        st.exception(e)