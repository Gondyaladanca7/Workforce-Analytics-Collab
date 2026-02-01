# pages/2_Employee_Records.py
"""
Employee Records — Workforce Intelligence System (FULL CRUD)
View, search, edit, delete employees with role control.
"""

import streamlit as st
import pandas as pd
from utils import database as db
from utils.auth import require_login

# -------------------------
# Page Config & Auth
# -------------------------
st.set_page_config(page_title="Employee Records", page_icon="📄", layout="wide")
require_login()

role = st.session_state.get("role", "")
if role not in ["Admin", "HR", "Manager"]:
    st.warning("⚠️ You do not have permission to view this page.")
    st.stop()

st.title("📄 Employee Records")

# -------------------------
# Load Data
# -------------------------
try:
    df = db.fetch_employees()
except Exception as e:
    st.error("Failed to fetch employee data.")
    st.exception(e)
    df = pd.DataFrame()

if df.empty:
    st.info("No employee records available.")
    st.stop()

# Add SR No
df = df.sort_values("Emp_ID")
df_display = df.reset_index(drop=True)
df_display.insert(0, "SR_No", range(1, len(df_display) + 1))

# -------------------------
# Search
# -------------------------
st.subheader("🔍 Search Employee")
search = st.text_input("Search by Name / Department / Role").lower()

filtered_df = df_display.copy()
if search:
    filtered_df = filtered_df[
        filtered_df["Name"].str.lower().str.contains(search, na=False) |
        filtered_df["Department"].str.lower().str.contains(search, na=False) |
        filtered_df["Role"].str.lower().str.contains(search, na=False)
    ]

st.dataframe(
    filtered_df[["SR_No","Emp_ID","Name","Department","Role","Status","Salary","Location"]],
    use_container_width=True,
    height=350
)

# -------------------------
# Edit / Delete Section
# -------------------------
if role in ["Admin", "HR"]:
    st.divider()
    st.subheader("✏️ Edit / Delete Employee")

    emp_options = filtered_df["Emp_ID"].astype(str) + " - " + filtered_df["Name"]
    selected = st.selectbox("Select Employee", emp_options)

    emp_id = int(selected.split(" - ")[0])
    emp_row = df[df["Emp_ID"] == emp_id].iloc[0]

    with st.form("edit_employee_form"):
        name = st.text_input("Name", emp_row["Name"])
        age = st.number_input("Age", value=int(emp_row["Age"]))
        gender = st.selectbox("Gender", ["Male","Female"], index=0 if emp_row["Gender"]=="Male" else 1)
        dept = st.text_input("Department", emp_row["Department"])
        role_input = st.text_input("Role", emp_row["Role"])
        skills = st.text_input("Skills (Python:4;SQL:3)", emp_row["Skills"])
        status = st.selectbox("Status", ["Active","Resigned"], index=0 if emp_row["Status"]=="Active" else 1)
        salary = st.number_input("Salary", value=int(emp_row["Salary"]))
        location = st.text_input("Location", emp_row["Location"])

        update_btn = st.form_submit_button("Update Employee")
        delete_btn = st.form_submit_button("Delete Employee")

        if update_btn:
            try:
                db.update_employee(emp_id, {
                    "Name": name,
                    "Age": age,
                    "Gender": gender,
                    "Department": dept,
                    "Role": role_input,
                    "Skills": skills,
                    "Status": status,
                    "Salary": salary,
                    "Location": location
                })
                st.success("✅ Employee updated successfully.")
                st.rerun()

            except Exception as e:
                st.error("❌ Failed to update employee.")
                st.exception(e)

        if delete_btn:
            try:
                db.delete_employee(emp_id)
                st.success("🗑️ Employee deleted successfully.")
                st.rerun()

            except Exception as e:
                st.error("❌ Failed to delete employee.")
                st.exception(e)

else:
    st.info("Only Admin and HR can edit or delete employees.")
