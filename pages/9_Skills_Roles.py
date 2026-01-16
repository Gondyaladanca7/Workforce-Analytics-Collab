# pages/9_Skills_Roles.py
"""
Employee Skill Inventory & Role Mapping — Workforce Intelligence System
Visualize skills, suggest roles, and update employee roles safely.
"""

import streamlit as st
import pandas as pd
from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_summary_pdf
import io

# -----------------------
# Authentication
# -----------------------
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "Unknown")

st.title("🧰 Skill Inventory & Role Mapping")

# -----------------------
# Load Employees Safely
# -----------------------
try:
    emp_df = db.fetch_employees()
except Exception as e:
    st.error("❌ Failed to load employees.")
    st.exception(e)
    emp_df = pd.DataFrame(columns=["Emp_ID","Name","Department","Role","Skills","Location"])

if emp_df.empty:
    st.info("⚠️ No employee data available.")

# -----------------------
# Sidebar Filters
# -----------------------
st.sidebar.header("Filters")
dept_filter = st.sidebar.selectbox(
    "Department",
    ["All"] + sorted(emp_df["Department"].dropna().unique()) if not emp_df.empty else ["All"]
)
role_filter = st.sidebar.selectbox(
    "Role",
    ["All"] + sorted(emp_df["Role"].dropna().unique()) if not emp_df.empty else ["All"]
)
skill_search = st.sidebar.text_input("Search by Skill").lower().strip() if not emp_df.empty else ""

filtered_df = emp_df.copy() if not emp_df.empty else pd.DataFrame()
if not filtered_df.empty:
    if dept_filter != "All":
        filtered_df = filtered_df[filtered_df["Department"] == dept_filter]
    if role_filter != "All":
        filtered_df = filtered_df[filtered_df["Role"] == role_filter]
    if skill_search:
        filtered_df = filtered_df[
            filtered_df["Skills"].str.replace(";", ",").str.lower().str.contains(skill_search, na=False)
        ]

# -----------------------
# Employee Skill Inventory Table
# -----------------------
st.subheader("👩‍💼 Employee Skill Inventory")
st.dataframe(
    filtered_df[["Emp_ID", "Name", "Department", "Role", "Skills", "Location"]] 
    if not filtered_df.empty else pd.DataFrame(
        columns=["Emp_ID","Name","Department","Role","Skills","Location"]
    ),
    height=400
)

st.markdown("---")

# -----------------------
# Skill Analytics
# -----------------------
st.subheader("📊 Skill Analytics")
if not filtered_df.empty:
    # Top Skills
    all_skills = filtered_df["Skills"].dropna().str.replace(";", ",").str.split(",").explode().str.strip()
    top_skills = all_skills.value_counts().head(10)
    st.markdown("**Top 10 Skills Across Employees**")
    st.bar_chart(top_skills)

    # Department-wise Skill Distribution
    st.markdown("**Department-wise Skills Count**")
    dept_skills = filtered_df.groupby("Department")["Skills"].apply(
        lambda x: x.str.replace(";", ",").str.split(",").sum()
    )
    dept_skills = dept_skills.explode().value_counts().sort_values(ascending=False)
    st.bar_chart(dept_skills)

# -----------------------
# Role Assignment / Suggestions
# -----------------------
st.markdown("---")
st.subheader("🔄 Role Mapping & Suggestions")
if not filtered_df.empty:
    emp_selection = st.selectbox(
        "Select Employee",
        filtered_df["Emp_ID"].astype(str) + " - " + filtered_df["Name"]
    )
    emp_id = int(emp_selection.split(" - ")[0])
    emp_row = emp_df[emp_df["Emp_ID"] == emp_id].iloc[0]

    st.markdown(f"**Current Role:** {emp_row['Role']}")
    st.markdown(f"**Skills:** {emp_row['Skills']}")

    # Suggest roles based on skills
    skill_set = set(emp_row["Skills"].replace(";", ",").split(", ")) if emp_row["Skills"] else set()
    role_map = {
        "HR": {"HR Manager", "HR Executive"},
        "IT": {"Developer", "SysAdmin", "IT Manager"},
        "Sales": {"Sales Executive", "Sales Manager"},
        "Finance": {"Accountant", "Finance Manager"},
        "Marketing": {"Marketing Executive", "Marketing Manager"},
        "Support": {"Support Executive", "Support Manager"}
    }

    suggested_roles = []
    for dept, roles in role_map.items():
        for role_name in roles:
            if any(word.lower() in skill.lower() for word in role_name.split() for skill in skill_set):
                suggested_roles.append(role_name)
    if not suggested_roles:
        suggested_roles = ["No strong match found"]

    st.markdown("**Suggested Roles Based on Skills:**")
    st.write(", ".join(suggested_roles))

# -----------------------
# Update Employee Role
# -----------------------
st.markdown("---")
st.subheader("✏️ Update Employee Role")
if not filtered_df.empty:
    new_role = st.selectbox("Select New Role", ["Keep Current"] + sorted(emp_df["Role"].dropna().unique()))
    if st.button("Update Role"):
        if new_role != "Keep Current":
            try:
                db.update_employee(emp_id, {"Role": new_role})
                st.success(f"Role updated to '{new_role}'")
                st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
                st.experimental_rerun()
            except Exception as e:
                st.error("❌ Failed to update role.")
                st.exception(e)
        else:
            st.info("Role unchanged.")
