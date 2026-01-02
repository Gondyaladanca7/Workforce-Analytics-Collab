"""
Workforce Intelligence System
- Role-based workforce analytics platform
- Modular architecture
- 2026–2028 ready
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import random
import io
import importlib

# -------------------------
# Local utilities
# -------------------------
from utils import database as db
from utils.auth import require_login, logout_user, show_role_badge
from utils.analytics import (
    get_summary,
    department_distribution,
    gender_ratio,
    average_salary_by_dept
)
from utils.pdf_export import generate_summary_pdf

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="Workforce Intelligence System",
    page_icon="🏢",
    layout="wide"
)

# -------------------------
# Initialize Database
# -------------------------
try:
    db.initialize_all_tables()
    db.create_default_admin()   # 🔑 CRITICAL
except Exception as e:
    st.error("❌ Database initialization failed")
    st.exception(e)
    st.stop()

# -------------------------
# Authentication
# -------------------------
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "Unknown")

# -------------------------
# Load Employees
# -------------------------
try:
    df = db.fetch_employees()
except Exception as e:
    df = pd.DataFrame()
    st.error("Failed to load employees.")
    st.exception(e)

# -------------------------
# Auto-generate demo employees
# -------------------------
if df.empty:
    st.info("Generating demo workforce data...")

    def generate_employees(n=80):
        depts = ["HR", "IT", "Sales", "Finance", "Marketing", "Support"]
        roles = {
            "HR": ["HR Manager", "HR Executive"],
            "IT": ["Developer", "SysAdmin", "IT Manager"],
            "Sales": ["Sales Executive", "Sales Manager"],
            "Finance": ["Accountant", "Finance Manager"],
            "Marketing": ["Marketing Executive", "Marketing Manager"],
            "Support": ["Support Executive", "Support Manager"]
        }
        skills = [
            "Python", "SQL", "Excel", "Power BI",
            "Communication", "Leadership", "Analytics", "JavaScript"
        ]

        names_m = ["John", "Alex", "Michael", "David", "Chris", "Liam"]
        names_f = ["Sophia", "Emma", "Chloe", "Ava", "Mia", "Isabella"]

        employees = []
        for _ in range(n):
            gender = random.choice(["Male", "Female"])
            name = random.choice(names_m if gender == "Male" else names_f)
            dept = random.choice(depts)

            employees.append({
                "Name": name,
                "Age": random.randint(22, 60),
                "Gender": gender,
                "Department": dept,
                "Role": random.choice(roles[dept]),
                "Skills": ", ".join(random.sample(skills, 3)),
                "Join_Date": (
                    datetime.datetime.now()
                    - datetime.timedelta(days=random.randint(200, 3000))
                ).strftime("%Y-%m-%d"),
                "Resign_Date": "",
                "Status": "Active",
                "Salary": random.randint(30000, 120000),
                "Location": random.choice(
                    ["Bangalore", "Delhi", "Mumbai", "Chennai", "Hyderabad"]
                )
            })

        return pd.DataFrame(employees)

    gen_df = generate_employees()
    for _, row in gen_df.iterrows():
        db.add_employee(row.to_dict())

    df = db.fetch_employees()
    st.success("✅ Demo workforce created successfully")

# -------------------------
# Sidebar Navigation
# -------------------------
if role in ["Admin", "Manager", "HR"]:
    modules = [
        "Employees",
        "Tasks",
        "Mood Tracker",
        "Feedback",
        "Projects",
        "Attendance",
        "Notifications",
        "Analytics"
    ]
else:
    modules = [
        "Tasks",
        "Mood Tracker",
        "Feedback",
        "Attendance",
        "Notifications",
        "Analytics"
    ]

selected = st.sidebar.radio("📂 Modules", modules)

# -------------------------
# Routing
# -------------------------
if selected == "Employees" and role in ["Admin", "Manager", "HR"]:
    st.header("👩‍💼 Employee Management")
    st.dataframe(
        df[["Emp_ID", "Name", "Department", "Role", "Status", "Join_Date"]],
        height=500
    )

elif selected == "Tasks":
    from pages import tasks
    tasks.show()

elif selected == "Mood Tracker":
    from pages import mood_tracker
    mood_tracker.show()

elif selected == "Feedback":
    from pages import feedback
    feedback.show()

elif selected == "Projects":
    projects = importlib.import_module("pages.10_Projects")
    projects.show()

elif selected == "Attendance":
    attendance = importlib.import_module("pages.11_Attendance")
    attendance.show()

elif selected == "Notifications":
    notifications = importlib.import_module("pages.12_Notifications")
    notifications.show()

elif selected == "Analytics":
    st.header("📊 Workforce Intelligence Analytics")

    summary = get_summary(df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Employees", summary["total"])
    c2.metric("Active", summary["active"])
    c3.metric("Resigned", summary["resigned"])

    # Department distribution
    dept = department_distribution(df)
    fig1, ax1 = plt.subplots()
    ax1.bar(dept.index, dept.values)
    ax1.set_title("Employees by Department")
    plt.xticks(rotation=30)
    st.pyplot(fig1)

    # Gender ratio
    g = gender_ratio(df)
    fig2, ax2 = plt.subplots()
    ax2.pie(g.values, labels=g.index, autopct="%1.1f%%")
    ax2.set_title("Gender Ratio")
    st.pyplot(fig2)

    # Salary
    sal = average_salary_by_dept(df)
    fig3, ax3 = plt.subplots()
    ax3.bar(sal.index, sal.values)
    ax3.set_title("Average Salary by Department")
    plt.xticks(rotation=30)
    st.pyplot(fig3)

    # PDF Export
    st.subheader("📄 Export Report")
    buffer = io.BytesIO()

    if st.button("Generate PDF"):
        generate_summary_pdf(
            buffer=buffer,
            total=summary["total"],
            active=summary["active"],
            resigned=summary["resigned"],
            df=df,
            mood_df=db.fetch_mood(),
            dept_fig=fig1,
            gender_fig=fig2,
            salary_fig=fig3,
            title="Workforce Intelligence Report"
        )

        st.download_button(
            "Download PDF",
            buffer,
            file_name="workforce_report.pdf",
            mime="application/pdf"
        )
