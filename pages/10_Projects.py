# pages/10_Projects.py
"""
Project Health Tracker — Workforce Intelligence System
Rich content:
- KPI cards (total, healthy, at risk, critical, avg progress)
- Add / Edit / Delete projects
- Health scoring (progress + mood + attendance)
- Plotly interactive charts with hover
- Gantt-style timeline view
- Per-project drill-down
- PDF export with graph
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import datetime
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -------------------------
# Auth
# -------------------------
st.set_page_config(page_title="Project Health Tracker", page_icon="📈", layout="wide")
require_login(roles_allowed=["Admin", "Manager", "HR"])
show_role_badge()
logout_user()

st.title("📈 Project Health Tracker")
st.caption("Real-time project health scored from progress, team mood and attendance")

# -------------------------
# Load Data
# -------------------------
try:
    project_df   = db.fetch_projects()
    emp_df       = db.fetch_employees()
    attendance_df = db.fetch_attendance()
    mood_df      = db.fetch_mood_logs()
except Exception as e:
    st.error("Failed to load data.")
    st.exception(e)
    st.stop()

# -------------------------
# Add New Project (Admin / Manager)
# -------------------------
role = st.session_state.get("role", "Manager")

with st.expander("➕ Add New Project", expanded=False):
    if not emp_df.empty:
        with st.form("add_project_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            proj_name  = col1.text_input("Project Name *")
            owner_opts = (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist()
            owner_sel  = col2.selectbox("Project Owner *", owner_opts)
            status_sel = col1.selectbox("Status", ["Active", "On Hold", "Completed", "Cancelled"])
            progress   = col2.slider("Progress (%)", 0, 100, 0)
            start_date = col1.date_input("Start Date", datetime.date.today())
            due_date   = col2.date_input("Due Date",   datetime.date.today() + datetime.timedelta(days=30))
            add_btn    = st.form_submit_button("Add Project")

            if add_btn:
                if not proj_name.strip():
                    st.error("Project name is required.")
                else:
                    owner_id = int(owner_sel.split(" - ")[0])
                    conn = db.connect_db()
                    cur  = conn.cursor()
                    cur.execute("""
                        INSERT INTO projects (project_name, owner_emp_id, status, progress, start_date, due_date)
                        VALUES (?,?,?,?,?,?)
                    """, (proj_name.strip(), owner_id, status_sel, progress,
                          str(start_date), str(due_date)))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Project '{proj_name}' added!")
                    st.rerun()
    else:
        st.info("Add employees before creating projects.")

# -------------------------
# Reload after possible add
# -------------------------
project_df = db.fetch_projects()

if project_df.empty:
    st.info("No projects yet. Use the form above to add your first project.")
    st.stop()

# -------------------------
# Map Employee Names
# -------------------------
emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict() if not emp_df.empty else {}
project_df["Owner"] = project_df["owner_emp_id"].map(emp_map).fillna(
    project_df["owner_emp_id"].astype(str)
)

# -------------------------
# Scoring helpers
# -------------------------
def attendance_score(emp_id):
    if attendance_df.empty:
        return 0
    emp_att = attendance_df[attendance_df["emp_id"] == emp_id]
    if emp_att.empty:
        return 5
    present = len(emp_att[emp_att["status"].str.lower() == "present"])
    ratio   = present / len(emp_att)
    if ratio > 0.8:  return 20
    if ratio > 0.5:  return 10
    return 0

def mood_score(emp_id):
    if mood_df.empty:
        return 0
    emp_mood = mood_df[mood_df["emp_id"] == emp_id]
    if emp_mood.empty:
        return 5
    last = emp_mood.sort_values("log_date").iloc[-1]
    remark = str(last.get("remarks", ""))
    if "Happy"   in remark: return 20
    if "Neutral" in remark: return 10
    return 0

def days_to_due(due_str):
    try:
        due = pd.to_datetime(due_str).date()
        return (due - datetime.date.today()).days
    except Exception:
        return 999

# -------------------------
# Compute Health for all projects
# -------------------------
health_rows = []
for _, row in project_df.iterrows():
    progress  = int(row.get("progress", 0))
    owner_id  = row.get("owner_emp_id")
    mood      = mood_score(owner_id)
    att       = attendance_score(owner_id)
    days_left = days_to_due(row.get("due_date", ""))

    # Deadline penalty
    deadline_bonus = 0
    if days_left < 0:
        deadline_bonus = -20   # overdue
    elif days_left < 7:
        deadline_bonus = -10   # due soon

    health_score = min(100, max(0, progress + mood + att + deadline_bonus))

    if row.get("status") == "Completed":
        health_status = "✅ Completed"
        health_color  = "#22c55e"
    elif row.get("status") == "Cancelled":
        health_status = "⛔ Cancelled"
        health_color  = "#94a3b8"
    elif health_score >= 70:
        health_status = "🟢 Healthy"
        health_color  = "#22c55e"
    elif health_score >= 40:
        health_status = "🟡 At Risk"
        health_color  = "#f59e0b"
    else:
        health_status = "🔴 Critical"
        health_color  = "#ef4444"

    health_rows.append({
        "Project ID":    row["project_id"],
        "Project":       row["project_name"],
        "Owner":         row["Owner"],
        "Status":        row.get("status", "Active"),
        "Progress (%)":  progress,
        "Health Score":  health_score,
        "Health Status": health_status,
        "_color":        health_color,
        "Start Date":    row.get("start_date", ""),
        "Due Date":      row.get("due_date", ""),
        "Days Left":     days_left,
    })

health_df = pd.DataFrame(health_rows)

# -------------------------
# KPI Cards
# -------------------------
st.subheader("📊 Project Overview")

total_p     = len(health_df)
healthy_p   = len(health_df[health_df["Health Status"].str.contains("Healthy")])
at_risk_p   = len(health_df[health_df["Health Status"].str.contains("At Risk")])
critical_p  = len(health_df[health_df["Health Status"].str.contains("Critical")])
completed_p = len(health_df[health_df["Health Status"].str.contains("Completed")])
avg_prog    = int(health_df["Progress (%)"].mean()) if total_p > 0 else 0
overdue_p   = len(health_df[health_df["Days Left"] < 0])

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("📁 Total Projects",  total_p)
k2.metric("🟢 Healthy",         healthy_p)
k3.metric("🟡 At Risk",         at_risk_p)
k4.metric("🔴 Critical",        critical_p)
k5.metric("✅ Completed",        completed_p)
k6.metric("⏰ Overdue",          overdue_p)

st.divider()

# -------------------------
# Filters
# -------------------------
col_f1, col_f2 = st.columns(2)
filter_status = col_f1.selectbox("Filter by Status", ["All", "Active", "Completed", "On Hold", "Cancelled"])
filter_health = col_f2.selectbox("Filter by Health", ["All", "🟢 Healthy", "🟡 At Risk", "🔴 Critical", "✅ Completed"])

display_df = health_df.copy()
if filter_status != "All":
    display_df = display_df[display_df["Status"] == filter_status]
if filter_health != "All":
    display_df = display_df[display_df["Health Status"].str.contains(filter_health.split(" ", 1)[-1])]

# -------------------------
# Project Health Table
# -------------------------
st.subheader("📋 Project Health Overview")
st.dataframe(
    display_df.drop(columns=["_color"], errors="ignore"),
    use_container_width=True,
    height=320
)

st.divider()

# -------------------------
# Charts Row 1
# -------------------------
st.subheader("📈 Health Analytics")
ch1, ch2 = st.columns(2)

with ch1:
    # Health status distribution
    hcount = health_df["Health Status"].value_counts()
    color_map = {
        "🟢 Healthy": "#22c55e", "🟡 At Risk": "#f59e0b",
        "🔴 Critical": "#ef4444", "✅ Completed": "#667eea", "⛔ Cancelled": "#94a3b8"
    }
    fig_h = go.Figure(go.Pie(
        labels=hcount.index.tolist(),
        values=hcount.values.tolist(),
        hole=0.45,
        marker=dict(colors=[color_map.get(l, "#667eea") for l in hcount.index]),
        hovertemplate="<b>%{label}</b><br>%{value} projects (%{percent})<extra></extra>"
    ))
    fig_h.update_layout(
        title="Projects by Health Status",
        height=360, paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_h, use_container_width=True)

with ch2:
    # Progress bar chart per project (top 15)
    top15 = health_df.nlargest(15, "Progress (%)")
    fig_p = go.Figure(go.Bar(
        y=top15["Project"].tolist(),
        x=top15["Progress (%)"].tolist(),
        orientation="h",
        text=[f"{v}%" for v in top15["Progress (%)"]],
        textposition="outside",
        marker_color=top15["_color"].tolist(),
        hovertemplate="<b>%{y}</b><br>Progress: %{x}%<extra></extra>"
    ))
    fig_p.update_layout(
        title="Project Progress (Top 15)",
        xaxis=dict(range=[0, 115], title="Progress (%)"),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=360
    )
    st.plotly_chart(fig_p, use_container_width=True)

# -------------------------
# Charts Row 2
# -------------------------
ch3, ch4 = st.columns(2)

with ch3:
    # Health score scatter
    fig_scatter = px.scatter(
        health_df,
        x="Progress (%)",
        y="Health Score",
        color="Health Status",
        size="Health Score",
        hover_data=["Project", "Owner", "Days Left"],
        title="Progress vs Health Score",
        color_discrete_map={
            "🟢 Healthy": "#22c55e", "🟡 At Risk": "#f59e0b",
            "🔴 Critical": "#ef4444", "✅ Completed": "#667eea"
        }
    )
    fig_scatter.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=360
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with ch4:
    # Days Left distribution
    active_proj = health_df[~health_df["Health Status"].str.contains("Completed|Cancelled")]
    if not active_proj.empty:
        fig_days = px.bar(
            active_proj.sort_values("Days Left"),
            x="Project",
            y="Days Left",
            color="Days Left",
            color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
            title="Days Until Due Date (Active Projects)",
            hover_data=["Health Score", "Owner"]
        )
        fig_days.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-35, height=360
        )
        st.plotly_chart(fig_days, use_container_width=True)
    else:
        st.info("No active projects.")

# -------------------------
# Gantt-style Timeline
# -------------------------
st.divider()
st.subheader("📅 Project Timeline")

gantt_df = project_df.copy()
gantt_df["Start"] = pd.to_datetime(gantt_df["start_date"], errors="coerce")
gantt_df["Finish"] = pd.to_datetime(gantt_df["due_date"], errors="coerce")
gantt_df = gantt_df.dropna(subset=["Start", "Finish"])
gantt_df["Owner"] = gantt_df["owner_emp_id"].map(emp_map).fillna("Unknown")

if not gantt_df.empty:
    # merge health status
    status_map = health_df.set_index("Project ID")["Health Status"].to_dict()
    gantt_df["Health"] = gantt_df["project_id"].map(status_map).fillna("Unknown")

    color_scale = {
        "🟢 Healthy": "#22c55e", "🟡 At Risk": "#f59e0b",
        "🔴 Critical": "#ef4444", "✅ Completed": "#667eea",
        "⛔ Cancelled": "#94a3b8", "Unknown": "#94a3b8"
    }

    fig_gantt = px.timeline(
        gantt_df,
        x_start="Start",
        x_end="Finish",
        y="project_name",
        color="Health",
        hover_data=["Owner", "status", "progress"],
        title="Project Timelines",
        color_discrete_map=color_scale
    )
    fig_gantt.update_yaxes(autorange="reversed")
    fig_gantt.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=max(350, len(gantt_df) * 35)
    )
    st.plotly_chart(fig_gantt, use_container_width=True)
else:
    st.info("Add start and due dates to projects to see the timeline.")

# -------------------------
# Edit / Delete Project
# -------------------------
st.divider()
st.subheader("✏️ Edit / Delete Project")

if not health_df.empty:
    proj_options = health_df["Project ID"].astype(str) + " — " + health_df["Project"]
    sel_proj = st.selectbox("Select Project", proj_options.tolist())
    sel_id   = int(sel_proj.split(" — ")[0])
    sel_row  = project_df[project_df["project_id"] == sel_id].iloc[0]

    with st.form("edit_project_form"):
        ec1, ec2 = st.columns(2)
        e_name    = ec1.text_input("Project Name",   sel_row["project_name"])
        e_status  = ec2.selectbox("Status",          ["Active","On Hold","Completed","Cancelled"],
                                  index=["Active","On Hold","Completed","Cancelled"].index(sel_row["status"])
                                  if sel_row["status"] in ["Active","On Hold","Completed","Cancelled"] else 0)
        e_prog    = ec1.slider("Progress (%)", 0, 100, int(sel_row.get("progress", 0)))
        try:
            e_start = ec2.date_input("Start Date", pd.to_datetime(sel_row["start_date"]).date())
            e_due   = ec1.date_input("Due Date",   pd.to_datetime(sel_row["due_date"]).date())
        except Exception:
            e_start = ec2.date_input("Start Date", datetime.date.today())
            e_due   = ec1.date_input("Due Date",   datetime.date.today())

        upd_btn = st.form_submit_button("💾 Update Project")
        del_btn = st.form_submit_button("🗑️ Delete Project")

        if upd_btn:
            conn = db.connect_db()
            cur  = conn.cursor()
            cur.execute("""
                UPDATE projects SET project_name=?, status=?, progress=?, start_date=?, due_date=?
                WHERE project_id=?
            """, (e_name, e_status, e_prog, str(e_start), str(e_due), sel_id))
            conn.commit(); conn.close()
            st.success("✅ Project updated.")
            st.rerun()

        if del_btn:
            conn = db.connect_db()
            cur  = conn.cursor()
            cur.execute("DELETE FROM projects WHERE project_id=?", (sel_id,))
            conn.commit(); conn.close()
            st.success("🗑️ Project deleted.")
            st.rerun()

# -------------------------
# PDF Export
# -------------------------
st.divider()
st.subheader("📄 Download Project Report PDF")

if st.button("📋 Generate PDF"):
    # Build matplotlib chart for PDF
    hcount = health_df["Health Status"].value_counts()
    color_list = [{"🟢 Healthy": "#22c55e","🟡 At Risk":"#f59e0b","🔴 Critical":"#ef4444",
                   "✅ Completed":"#667eea","⛔ Cancelled":"#94a3b8"}.get(l,"#667eea") for l in hcount.index]
    fig_pdf, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar([l.split(" ",1)[-1] for l in hcount.index], hcount.values, color=color_list)
    ax.set_title("Projects by Health Status"); ax.set_ylabel("Count")
    for bar in bars:
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    buf = io.BytesIO()
    fig_pdf.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    project_png = buf.read()
    plt.close(fig_pdf)

    pdf_buffer = io.BytesIO()
    try:
        generate_master_report(
            buffer=pdf_buffer,
            employees_df=emp_df,
            attendance_df=attendance_df,
            mood_df=mood_df,
            projects_df=health_df.drop(columns=["_color"], errors="ignore"),
            notifications_df=pd.DataFrame(),
            project_fig=project_png
        )
        pdf_buffer.seek(0)
        st.download_button("⬇️ Download PDF", pdf_buffer,
                           "project_health_report.pdf", "application/pdf")
    except Exception as e:
        st.error("PDF generation failed.")
        st.exception(e)