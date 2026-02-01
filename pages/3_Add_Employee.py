# pages/3_Add_Employee.py

import streamlit as st
import pandas as pd
from utils import database as db
from utils.auth import require_login

st.set_page_config(page_title="Add Employee", page_icon="➕", layout="wide")
require_login()

role = st.session_state.get("role", "")
if role not in ["Admin", "HR"]:
    st.warning("⚠️ You do not have permission to add employees.")
    st.stop()

st.title("➕ Add New Employee")

with st.form("add_employee_form", clear_on_submit=True):
    emp_name = st.text_input("Name *")
    age = st.number_input("Age", min_value=18, max_value=70)
    gender_val = st.selectbox("Gender *", ["Male", "Female"])
    department = st.text_input("Department *")
    role_input = st.text_input("Role *")
    skills = st.text_input("Skills (format: Python:4;SQL:3;Excel:5)")
    join_date = st.date_input("Join Date *")
    status = st.selectbox("Status *", ["Active", "Resigned"])
    resign_date = st.date_input("Resign Date (if resigned)")
    salary = st.number_input("Salary", min_value=0)
    location = st.text_input("Location *")

    submit = st.form_submit_button("Add Employee")

    if submit:
        if not all([emp_name, department, role_input, join_date, location]):
            st.error("Please fill all required fields (*)")
        else:
            new_row = {
                "user_id": None,
                "Name": emp_name,
                "Age": int(age),
                "Gender": gender_val,
                "Department": department,
                "Role": role_input,
                "Skills": skills or "Python:3",
                "Join_Date": str(join_date),
                "Resign_Date": str(resign_date) if status == "Resigned" else "",
                "Status": status,
                "Salary": float(salary),
                "Location": location
            }
            try:
                db.add_employee(new_row)
                st.success(f"✅ Employee {emp_name} added successfully!")
            except Exception as e:
                st.error("Failed to add employee.")
                st.exception(e)
