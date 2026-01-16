# pages/3_Add_Employee.py
"""
Add New Employee — Workforce Analytics System
Handles employee creation with role enforcement, validation, and database integration.
"""

import streamlit as st
import pandas as pd
from utils import database as db
from utils.auth import require_login

# -------------------------
# Page Config & Auth
# -------------------------
st.set_page_config(page_title="Add Employee", page_icon="➕", layout="wide")
require_login()

# Only Admin and HR can add employees
role = st.session_state.get("role", "")
if role not in ["Admin", "HR"]:
    st.warning("⚠️ You do not have permission to add employees.")
    st.stop()

st.title("➕ Add New Employee")

# -------------------------
# Fetch current employees
# -------------------------
try:
    df = db.fetch_employees()
except Exception:
    df = pd.DataFrame(columns=[
        "Emp_ID","Name","Age","Gender","Department","Role",
        "Skills","Join_Date","Resign_Date","Status","Salary","Location"
    ])

# -------------------------
# Add Employee Form
# -------------------------
with st.form("add_employee_form", clear_on_submit=True):
    # Auto-generate next Emp_ID
    try:
        next_emp_id = int(df["Emp_ID"].max()) + 1 if ("Emp_ID" in df.columns and not df["Emp_ID"].empty) else 1
    except Exception:
        next_emp_id = 1

    emp_id = st.number_input("Employee ID", value=next_emp_id, step=1)
    emp_name = st.text_input("Name *")
    age = st.number_input("Age", min_value=18, max_value=70, step=1)
    gender_val = st.selectbox("Gender *", ["Male","Female"])
    department = st.text_input("Department *")
    role_input = st.text_input("Role *")
    skills = st.text_input("Skills (semicolon separated)")
    join_date = st.date_input("Join Date *")
    status = st.selectbox("Status *", ["Active","Resigned"])
    resign_date = st.date_input("Resign Date (if resigned)")

    if status == "Active":
        resign_date = ""

    salary = st.number_input("Salary", min_value=0, step=1000)
    location = st.text_input("Location *")

    submit = st.form_submit_button("Add Employee")

    # -------------------------
    # Form submission handling
    if submit:
        # Validation
        required_fields = [emp_name, department, role_input, join_date, status, location]
        if not all(required_fields):
            st.error("Please fill in all required fields (*)")
        else:
            new_row = {
                "Emp_ID": int(emp_id),
                "Name": emp_name,
                "Age": int(age),
                "Gender": gender_val,
                "Department": department,
                "Role": role_input,
                "Skills": skills or "NA",
                "Join_Date": str(join_date),
                "Resign_Date": str(resign_date) if status=="Resigned" else "",
                "Status": status,
                "Salary": float(salary),
                "Location": location
            }
            try:
                db.add_employee(new_row)
                st.success(f"Employee {emp_name} added successfully!")

                # Optional: auto-refresh employee list in session state
                st.session_state["employee_update_trigger"] = not st.session_state.get("employee_update_trigger", False)

                # Optionally export updated list
                if st.checkbox("Export updated employee list to CSV"):
                    df_updated = db.fetch_employees()
                    df_updated.to_csv("employee_records.csv", index=False)
                    st.success("CSV exported successfully!")

            except Exception as e:
                st.error("Failed to add employee to database.")
                st.exception(e)
# -------------------------

