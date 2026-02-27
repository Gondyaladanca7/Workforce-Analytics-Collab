"""
Workforce Intelligence System
- Role-based workforce analytics platform
- Modular architecture
- Streamlit native pages
- FIXED: employee cap raised to 500
- ADDED: CSV import button in sidebar
"""

import streamlit as st
import pandas as pd
import datetime
import random
import io

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="Workforce Intelligence System",
    page_icon="🏢",
    layout="wide"
)

# -------------------------
# Local utilities
# -------------------------
from utils import database as db
from utils.auth import require_login, logout_user, show_role_badge

# -------------------------
# Initialize Database
# -------------------------
try:
    db.initialize_all_tables()
    db.create_default_admin()
except Exception as e:
    st.error("❌ Database initialization failed")
    st.exception(e)
    st.stop()

# -------------------------
# Authentication
# -------------------------
require_login()
role     = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "Unknown")

# -------------------------
# Sidebar (after login)
# -------------------------
if st.session_state.get("logged_in"):
    with st.sidebar:
        st.title("🏢 Workforce System")

        # User & Role badge
        st.markdown(f"👤 **User:** `{username}`")
        st.markdown(f"🧑‍💼 **Role:** `{role}`")

        # ── CSV IMPORT (Admin / HR only) ───────────────────────
        if role in ["Admin", "HR"]:
            st.divider()
            st.markdown("### 📥 Import Employee CSV")

            with st.expander("Upload CSV File", expanded=False):
                st.caption(
                    "CSV must have columns: **Name, Age, Gender, Department, "
                    "Role, Skills, Join_Date, Status, Salary, Location**\n\n"
                    "Optional: Resign_Date"
                )

                # Download sample template
                sample_data = {
                    "Name":        ["Aarav Sharma", "Priya Patel"],
                    "Age":         [28, 32],
                    "Gender":      ["Male", "Female"],
                    "Department":  ["IT", "HR"],
                    "Role":        ["Software Engineer", "HR Manager"],
                    "Skills":      ["Python:4;SQL:3", "Recruitment:5;Excel:4"],
                    "Join_Date":   ["2022-06-01", "2021-03-15"],
                    "Resign_Date": ["", ""],
                    "Status":      ["Active", "Active"],
                    "Salary":      [75000, 65000],
                    "Location":    ["Bangalore", "Mumbai"],
                }
                sample_df  = pd.DataFrame(sample_data)
                sample_csv = sample_df.to_csv(index=False).encode("utf-8")

                st.download_button(
                    "⬇️ Download Sample CSV",
                    sample_csv,
                    "employee_template.csv",
                    "text/csv",
                    use_container_width=True
                )

                uploaded_csv = st.file_uploader(
                    "Choose CSV file",
                    type=["csv"],
                    key="sidebar_csv_upload"
                )

                if uploaded_csv is not None:
                    try:
                        csv_df = pd.read_csv(uploaded_csv)

                        required_cols = ["Name", "Department", "Role", "Status"]
                        missing = [c for c in required_cols if c not in csv_df.columns]

                        if missing:
                            st.error(f"Missing columns: {missing}")
                        else:
                            # Fill optional columns with defaults
                            csv_df["Age"]         = csv_df.get("Age",         pd.Series([30] * len(csv_df))).fillna(30)
                            csv_df["Gender"]      = csv_df.get("Gender",      pd.Series(["Male"] * len(csv_df))).fillna("Male")
                            csv_df["Skills"]      = csv_df.get("Skills",      pd.Series(["Excel:3"] * len(csv_df))).fillna("Excel:3")
                            csv_df["Join_Date"]   = csv_df.get("Join_Date",   pd.Series([datetime.date.today().strftime("%Y-%m-%d")] * len(csv_df))).fillna(datetime.date.today().strftime("%Y-%m-%d"))
                            csv_df["Resign_Date"] = csv_df.get("Resign_Date", pd.Series([""] * len(csv_df))).fillna("")
                            csv_df["Salary"]      = csv_df.get("Salary",      pd.Series([50000] * len(csv_df))).fillna(50000)
                            csv_df["Location"]    = csv_df.get("Location",    pd.Series(["Unknown"] * len(csv_df))).fillna("Unknown")

                            st.dataframe(csv_df.head(5), use_container_width=True)
                            st.caption(f"Preview: {len(csv_df)} employees found")

                            if st.button("✅ Import All Employees", use_container_width=True, key="confirm_import"):
                                success = 0
                                errors  = 0
                                for _, row in csv_df.iterrows():
                                    try:
                                        db.add_employee({
                                            "Name":        str(row["Name"]),
                                            "Age":         int(row["Age"]),
                                            "Gender":      str(row["Gender"]),
                                            "Department":  str(row["Department"]),
                                            "Role":        str(row["Role"]),
                                            "Skills":      str(row["Skills"]),
                                            "Join_Date":   str(row["Join_Date"]),
                                            "Resign_Date": str(row["Resign_Date"]),
                                            "Status":      str(row["Status"]),
                                            "Salary":      float(row["Salary"]),
                                            "Location":    str(row["Location"]),
                                        })
                                        success += 1
                                    except Exception:
                                        errors += 1

                                if success:
                                    st.success(f"✅ {success} employees imported!")
                                if errors:
                                    st.warning(f"⚠️ {errors} rows skipped due to errors.")
                                st.rerun()

                    except Exception as e:
                        st.error(f"Failed to read CSV: {e}")

        st.divider()
        logout_user()

# -------------------------
# Load Employees
# -------------------------
try:
    df = db.fetch_employees()
except Exception as e:
    df = pd.DataFrame()
    st.error("❌ Failed to load employees.")
    st.exception(e)

# -------------------------
# Auto-generate demo employees if DB empty
# CAP RAISED: 500 employees max (was 80)
# -------------------------
if df.empty:
    st.info("No employees found. Generating demo workforce data (200 employees)...")

    def generate_employees(n=200):   # ← was 80, now 200 default, cap is 500
        FIRST_M = ["Arjun","Rahul","Vikram","Amit","Rohan","Karan","Nikhil","Suresh",
                   "Deepak","Manoj","Sanjay","Rajesh","Aditya","Vivek","Harsh","Priyanshu",
                   "Tushar","Gaurav","Yash","Ritesh","Dev","Ankit","Sahil","Mohit","Varun"]
        FIRST_F = ["Priya","Neha","Sneha","Anjali","Pooja","Kavya","Divya","Meera",
                   "Riya","Sonal","Tanvi","Shreya","Nidhi","Pallavi","Swati","Preeti",
                   "Ananya","Ishita","Kriti","Simran","Aarti","Bhavna","Rekha","Sunita","Geeta"]
        LAST    = ["Sharma","Verma","Singh","Gupta","Patel","Mehta","Joshi","Nair",
                   "Iyer","Rao","Reddy","Kumar","Malhotra","Kapoor","Saxena","Agarwal",
                   "Mishra","Pandey","Chauhan","Banerjee","Das","Bose","Shah","Desai","Pillai"]

        depts = {
            "IT":         ["Software Engineer","Senior Developer","DevOps Engineer","Tech Lead","IT Manager"],
            "HR":         ["HR Executive","HR Manager","Recruiter","L&D Specialist"],
            "Finance":    ["Accountant","Finance Analyst","Senior Accountant","Finance Manager"],
            "Sales":      ["Sales Executive","Sales Manager","Business Development","Key Account Manager"],
            "Marketing":  ["Marketing Executive","Content Writer","SEO Specialist","Marketing Manager"],
            "Support":    ["Support Executive","Support Lead","Customer Success Manager"],
            "Operations": ["Operations Executive","Operations Manager","Supply Chain Analyst"],
            "Legal":      ["Legal Counsel","Compliance Officer","Legal Executive"],
        }
        skills_map = {
            "IT":         ["Python","Java","JavaScript","SQL","React","AWS","Docker","Git"],
            "HR":         ["Communication","Recruitment","Excel","Onboarding","Training","Payroll"],
            "Finance":    ["Excel","Tally","SAP","Financial Modelling","Accounting","GST"],
            "Sales":      ["CRM","Negotiation","Communication","Lead Generation","Salesforce"],
            "Marketing":  ["SEO","Google Ads","Content Writing","Canva","Social Media","Analytics"],
            "Support":    ["Communication","Zendesk","CRM","Problem Solving","Customer Service"],
            "Operations": ["Excel","ERP","Logistics","SAP","Supply Chain","Project Management"],
            "Legal":      ["Contract Law","Compliance","Legal Research","Drafting","GDPR"],
        }
        locations = ["Bangalore","Mumbai","Delhi","Hyderabad","Chennai","Pune","Noida","Gurgaon"]
        dept_keys = list(depts.keys())
        weights   = [35, 18, 20, 28, 24, 20, 22, 5]

        n = min(n, 500)   # hard cap at 500
        employees = []
        random.seed(99)

        for i in range(n):
            gender = "Female" if i % 3 == 0 else "Male"
            fn   = random.choice(FIRST_F if gender == "Female" else FIRST_M)
            ln   = random.choice(LAST)
            dept = random.choices(dept_keys, weights=weights)[0]
            pool = skills_map[dept]
            chosen = random.sample(pool, min(random.randint(3, 4), len(pool)))
            skills = ";".join(f"{s}:{random.randint(2,5)}" for s in chosen)

            base = {"IT":70000,"HR":45000,"Finance":50000,"Sales":40000,
                    "Marketing":42000,"Support":35000,"Operations":45000,"Legal":60000}[dept]
            role_choice = random.choice(depts[dept])
            if any(x in role_choice for x in ["Manager","Lead","Head"]):
                salary = random.randint(base+30000, base+80000)
            else:
                salary = random.randint(base-5000, base+20000)

            days_ago  = random.randint(30, 1800)
            join_date = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
            status    = "Resigned" if random.random() < 0.15 else "Active"
            res_days  = random.randint(10, max(11, days_ago-10))
            resign    = (datetime.datetime.now() - datetime.timedelta(days=res_days)).strftime("%Y-%m-%d") if status == "Resigned" else ""

            employees.append({
                "Name": f"{fn} {ln}", "Age": random.randint(22, 55),
                "Gender": gender, "Department": dept, "Role": role_choice,
                "Skills": skills, "Join_Date": join_date, "Resign_Date": resign,
                "Status": status, "Salary": float(salary),
                "Location": random.choice(locations)
            })

        return pd.DataFrame(employees)

    gen_df = generate_employees(200)
    for _, row in gen_df.iterrows():
        db.add_employee(row.to_dict())

    st.success(f"✅ Demo workforce created: {len(gen_df)} employees")
    st.rerun()

# -------------------------
# Dashboard Metrics
# -------------------------
st.title("📊 Workforce Intelligence Dashboard")
st.caption("Central overview of workforce data")

total_emp    = len(df)
active_emp   = int((df["Status"] == "Active").sum())
resigned_emp = int((df["Status"] == "Resigned").sum())
dept_count   = int(df["Department"].nunique())
avg_sal      = int(df["Salary"].mean()) if "Salary" in df.columns and total_emp > 0 else 0
retention    = round(active_emp / total_emp * 100, 1) if total_emp > 0 else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("👥 Total Employees",  total_emp)
c2.metric("✅ Active",           active_emp)
c3.metric("🚪 Resigned",         resigned_emp)
c4.metric("🏢 Departments",      dept_count)
c5.metric("💰 Avg Salary",       f"₹{avg_sal:,}")

st.divider()

st.subheader("👩‍💼 Recent Employees")
st.dataframe(
    df[["Emp_ID", "Name", "Department", "Role", "Status", "Join_Date"]]
    .sort_values("Join_Date", ascending=False)
    .head(10),
    use_container_width=True
)

st.info(
    "📂 Use the **left sidebar** to navigate modules — Tasks, Attendance, "
    "Mood Tracker, Projects, Analytics, Feedback, Skills & Roles, Notifications, "
    "Email Center, AI Assistant, and AI Summary."
)