# pages/9_Skills_Roles.py
"""
Employee Skill Inventory & Role Mapping (FINAL + PDF GRAPH)
- Uses scaled skills like Python:4;SQL:3;Excel:5
- Proper analytics
- Better role suggestions
- Clean graph labels (no overlap)
- Professional layout
- Graph included in PDF
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -----------------------
# Authentication
# -----------------------
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
st.title("🧰 Skill Inventory & Role Mapping")

# -----------------------
# Load Employees
# -----------------------
try:
    emp_df = db.fetch_employees()
except Exception as e:
    st.error("❌ Failed to load employees.")
    st.exception(e)
    emp_df = pd.DataFrame(columns=["Emp_ID", "Name", "Department", "Role", "Skills"])

if emp_df.empty:
    st.info("No employee data available.")
    st.stop()

# -----------------------
# Helper: Parse skills with scale
# -----------------------
def parse_skills(skill_str):
    skills = []
    if pd.isna(skill_str) or not str(skill_str).strip():
        return skills

    parts = str(skill_str).replace(",", ";").split(";")
    for p in parts:
        if ":" in p:
            skill, level = p.split(":", 1)
            try:
                skills.append((skill.strip(), int(level.strip())))
            except:
                skills.append((skill.strip(), 1))
        else:
            skills.append((p.strip(), 1))
    return skills

# -----------------------
# Sidebar Filters
# -----------------------
st.sidebar.header("Filters")

dept_filter = st.sidebar.selectbox(
    "Department",
    ["All"] + sorted(emp_df["Department"].dropna().unique())
)

role_filter = st.sidebar.selectbox(
    "Role",
    ["All"] + sorted(emp_df["Role"].dropna().unique())
)

filtered_df = emp_df.copy()
if dept_filter != "All":
    filtered_df = filtered_df[filtered_df["Department"] == dept_filter]
if role_filter != "All":
    filtered_df = filtered_df[filtered_df["Role"] == role_filter]

# -----------------------
# Build Skill Table
# -----------------------
skill_rows = []

for _, row in filtered_df.iterrows():
    parsed = parse_skills(row["Skills"])
    for skill, level in parsed:
        skill_rows.append({
            "Emp_ID": row["Emp_ID"],
            "Name": row["Name"],
            "Department": row["Department"],
            "Role": row["Role"],
            "Skill": skill,
            "Level": level
        })

skill_df = pd.DataFrame(skill_rows)

st.subheader("👩‍💼 Employee Skill Inventory (Scaled)")
st.dataframe(skill_df, use_container_width=True)

# -----------------------
# Skill Analytics
# -----------------------
st.subheader("📊 Skill Analytics")

skill_png = None  # 👈 image for PDF

if not skill_df.empty:
    avg_skill = skill_df.groupby("Skill")["Level"].mean().sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(avg_skill.index, avg_skill.values)

    ax.set_title("Average Skill Level (1–5)")
    ax.set_ylabel("Level")
    ax.set_xlabel("Skills")
    ax.set_yticks([1, 2, 3, 4, 5])

    ax.set_xticks(range(len(avg_skill.index)))
    ax.set_xticklabels(avg_skill.index, rotation=45, ha="right")

    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{bar.get_height():.1f}",
            ha="center",
            va="bottom",
            fontsize=9
        )

    plt.tight_layout()
    st.pyplot(fig)

    # ✅ Convert graph to PNG for PDF
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    skill_png = buf.read()
    plt.close(fig)

    # Department-wise skill strength
    st.subheader("🏢 Department-wise Skill Strength")
    dept_skill = skill_df.groupby(["Department", "Skill"])["Level"].mean().reset_index()
    st.dataframe(dept_skill, use_container_width=True)

else:
    st.info("No skill data available.")

# -----------------------
# Role Suggestion
# -----------------------
st.subheader("🔄 Role Suggestions Based on Skills")

emp_choice = st.selectbox(
    "Select Employee",
    emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]
)

emp_id = int(emp_choice.split(" - ")[0])
emp_row = emp_df[emp_df["Emp_ID"] == emp_id].iloc[0]
parsed_skills = parse_skills(emp_row["Skills"])

st.markdown(f"**Current Role:** {emp_row['Role']}")
st.markdown(f"**Skills:** {emp_row['Skills']}")

role_map = {
    "Developer": ["Python", "Java", "JavaScript"],
    "Data Analyst": ["Python", "SQL", "Excel"],
    "Manager": ["Leadership", "Communication"],
    "HR Executive": ["Communication", "Management"],
    "Accountant": ["Excel", "Finance"],
}

suggested = []

for role_name, req_skills in role_map.items():
    match = 0
    for skill, level in parsed_skills:
        if skill in req_skills and level >= 3:
            match += 1
    if match >= 1:
        suggested.append(role_name)

if suggested:
    st.success("Suggested Roles: " + ", ".join(suggested))
else:
    st.info("No strong role match found.")

# -----------------------
# Update Role (Admin/HR)
# -----------------------
if role in ["Admin", "HR"]:
    st.subheader("✏️ Update Employee Role")
    new_role = st.text_input("New Role")

    if st.button("Update Role"):
        if new_role.strip():
            try:
                db.update_employee(emp_id, {"Role": new_role.strip()})
                st.success("Role updated successfully.")
                st.rerun()
            except Exception as e:
                st.error("Failed to update role.")
                st.exception(e)
        else:
            st.warning("Enter a role name.")

# -----------------------
# PDF EXPORT (WITH GRAPH)
# -----------------------
st.divider()
st.subheader("📄 Download Skills Report PDF")

if st.button("Download Skills PDF"):
    if skill_png is None:
        st.error("No graph available to export.")
    else:
        pdf_buffer = io.BytesIO()
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                attendance_df=None,
                mood_df=None,
                projects_df=skill_df,
                notifications_df=None,
                project_fig=skill_png  # 👈 graph in PDF
            )

            pdf_buffer.seek(0)

            st.download_button(
                "Download PDF",
                pdf_buffer,
                "skills_report.pdf",
                "application/pdf"
            )
        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)
