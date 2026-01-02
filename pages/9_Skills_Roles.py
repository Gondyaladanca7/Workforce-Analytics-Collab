# pages/9_Skills_Roles.py
import streamlit as st
import pandas as pd
from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db

def show():
    # -------------------------
    # Login & Role
    # -------------------------
    require_login()
    show_role_badge()
    logout_user()

    st.title("🧰 Skill Inventory & Role Mapping")

    # -------------------------
    # Load Employees
    # -------------------------
    try:
        emp_df = db.fetch_employees()
    except Exception as e:
        st.error("Failed to load employees.")
        st.exception(e)
        return

    if emp_df.empty:
        st.info("No employee data available.")
        return

    # -------------------------
    # Sidebar Filters
    # -------------------------
    st.sidebar.header("Filters")
    dept_filter = st.sidebar.selectbox("Department", ["All"] + sorted(emp_df["Department"].dropna().unique()))
    role_filter = st.sidebar.selectbox("Role", ["All"] + sorted(emp_df["Role"].dropna().unique()))
    skill_search = st.sidebar.text_input("Search by Skill").lower().strip()

    filtered_df = emp_df.copy()
    if dept_filter != "All":
        filtered_df = filtered_df[filtered_df["Department"] == dept_filter]
    if role_filter != "All":
        filtered_df = filtered_df[filtered_df["Role"] == role_filter]
    if skill_search:
        filtered_df = filtered_df[filtered_df["Skills"].str.lower().str.contains(skill_search, na=False)]

    st.subheader("👩‍💼 Employee Skill Inventory")
    st.dataframe(
        filtered_df[["Emp_ID", "Name", "Department", "Role", "Skills", "Location"]],
        height=400
    )

    st.markdown("---")

    # -------------------------
    # Skill Analytics
    # -------------------------
    st.subheader("📊 Skill Analytics")

    # Top Skills
    all_skills = filtered_df["Skills"].dropna().str.split(", ").explode()
    top_skills = all_skills.value_counts().head(10)
    st.markdown("**Top 10 Skills Across Employees**")
    st.bar_chart(top_skills)

    # Department-wise Skill Distribution
    st.markdown("**Department-wise Skills Count**")
    dept_skills = filtered_df.groupby("Department")["Skills"].apply(lambda x: x.str.split(", ").sum())
    dept_skills = dept_skills.explode().value_counts().sort_values(ascending=False)
    st.bar_chart(dept_skills)

    st.markdown("---")

    # -------------------------
    # Role Assignment / Suggestion
    # -------------------------
    st.subheader("🔄 Role Mapping & Suggestions")

    emp_selection = st.selectbox("Select Employee", filtered_df["Emp_ID"].astype(str) + " - " + filtered_df["Name"])
    emp_id = int(emp_selection.split(" - ")[0])
    emp_row = emp_df[emp_df["Emp_ID"] == emp_id].iloc[0]

    st.markdown(f"**Current Role:** {emp_row['Role']}")
    st.markdown(f"**Skills:** {emp_row['Skills']}")

    # Suggest possible roles based on skills
    skill_set = set(emp_row["Skills"].split(", "))
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
        for role in roles:
            # simple skill matching: role name keywords in skills
            if any(word.lower() in skill.lower() for word in role.split() for skill in skill_set):
                suggested_roles.append(role)

    if not suggested_roles:
        suggested_roles = ["No strong match found"]

    st.markdown("**Suggested Roles Based on Skills:**")
    st.write(", ".join(suggested_roles))

    st.markdown("---")

    # -------------------------
    # Update Employee Role
    # -------------------------
    st.subheader("✏️ Update Employee Role")
    new_role = st.selectbox("Select New Role", ["Keep Current"] + sorted(emp_df["Role"].unique()))
    if st.button("Update Role"):
        if new_role != "Keep Current":
            try:
                db.update_employee(emp_id, {"Role": new_role})
                st.success(f"Role updated to '{new_role}'")
                st.experimental_rerun()
            except Exception as e:
                st.error("Failed to update role.")
                st.exception(e)
        else:
            st.info("Role unchanged.")
