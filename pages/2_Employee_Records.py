# pages/2_📄_Employee_Records.py
"""
Employee Records — Workforce Analytics System
Displays all employee records in a searchable, filterable, and sortable table.
Integrates with utils.database, utils.analytics, and utils.pdf_export.
"""

import streamlit as st
import pandas as pd
from utils import database as db, analytics, pdf_export
from utils.auth import require_login

# -------------------------
# Page Config & Auth
# -------------------------
st.set_page_config(page_title="Employee Records", page_icon="📄", layout="wide")
require_login()

# Only Admin, HR, Manager can view employee records
role = st.session_state.get("role", "")
if role not in ["Admin", "HR", "Manager"]:
    st.warning("⚠️ You do not have permission to view this page.")
    st.stop()

st.title("📄 Employee Records")

# -------------------------
# Load employee data
# -------------------------
try:
    df = db.fetch_employees()
except Exception as e:
    st.error("Failed to fetch employee data from database.")
    st.exception(e)
    df = pd.DataFrame(columns=[
        "Emp_ID","Name","Age","Gender","Department","Role",
        "Skills","Join_Date","Resign_Date","Status","Salary","Location"
    ])

# -------------------------
# Sidebar Filters
st.sidebar.header("🔍 Filter Employee Data")

def safe_options(df_local, col):
    if col in df_local.columns:
        opts = sorted(df_local[col].dropna().unique().tolist())
        return ["All"] + opts
    return ["All"]

selected_dept = st.sidebar.selectbox("Department", safe_options(df, "Department"))
selected_status = st.sidebar.selectbox("Status", safe_options(df, "Status"))
selected_gender = st.sidebar.selectbox("Gender", safe_options(df, "Gender"))
selected_role = st.sidebar.selectbox("Role", safe_options(df, "Role"))
selected_skills = st.sidebar.selectbox("Skills", safe_options(df, "Skills"))

# Apply filters
filtered_df = df.copy()
if selected_dept != "All":
    filtered_df = filtered_df[filtered_df["Department"] == selected_dept]
if selected_status != "All":
    filtered_df = filtered_df[filtered_df["Status"] == selected_status]
if selected_gender != "All":
    filtered_df = filtered_df[filtered_df["Gender"] == selected_gender]
if selected_role != "All":
    filtered_df = filtered_df[filtered_df["Role"] == selected_role]
if selected_skills != "All":
    filtered_df = filtered_df[filtered_df["Skills"] == selected_skills]

# -------------------------
# Search
st.header("1️⃣ Search Employee Records")
search_term = st.text_input("Search by Name, ID, Skills, or Role").strip()
display_df = filtered_df.copy()
if search_term:
    cond = pd.Series([False]*len(display_df), index=display_df.index)
    for col in ["Name","Emp_ID","Skills","Role"]:
        if col in display_df.columns:
            cond = cond | display_df[col].astype(str).str.contains(search_term, case=False, na=False)
    display_df = display_df[cond]

# -------------------------
# Sorting
available_sort_cols = [c for c in ["Emp_ID","Name","Age","Salary","Join_Date","Department","Role","Skills"] if c in display_df.columns]
if not available_sort_cols:
    available_sort_cols = display_df.columns.tolist()
sort_col = st.selectbox("Sort by", options=available_sort_cols, index=0)
ascending = st.radio("Order", ["Ascending","Descending"], horizontal=True) == "Ascending"
try:
    if sort_col in display_df.columns:
        display_df = display_df.sort_values(by=sort_col, ascending=ascending, key=lambda s: s.astype(str))
except Exception:
    pass

# -------------------------
# Display Table
st.header("2️⃣ Employee Records Table")
try:
    st.dataframe(display_df, height=500)
except Exception:
    st.info("No employee records to display.")

# -------------------------
# Summary
st.header("3️⃣ Summary Statistics")
summary = analytics.get_summary(display_df) if not display_df.empty else {"total":0,"active":0,"resigned":0}
col1, col2, col3 = st.columns(3)
col1.metric("Total Employees", summary["total"])
col2.metric("Active Employees", summary["active"])
col3.metric("Resigned Employees", summary["resigned"])

# -------------------------
# Skill Inventory & Role Mapping
st.header("🔧 Skill Inventory & Role Mapping")
try:
    if not filtered_df.empty and "Skills" in filtered_df.columns and "Role" in filtered_df.columns:
        skill_rows = filtered_df.assign(Skill=filtered_df['Skills'].str.split(';')).explode('Skill')
        skill_rows['Skill'] = skill_rows['Skill'].str.strip()
        skill_role_counts = skill_rows.groupby(['Skill', 'Role']).size().reset_index(name='Count')
        st.subheader("Employee Count by Skill & Role")
        st.dataframe(skill_role_counts)

        # Top 10 Skills Bar Chart
        top_skills = skill_rows['Skill'].value_counts().head(10)
        st.subheader("Top 10 Skills in Workforce")
        st.bar_chart(top_skills)
    else:
        st.info("No skill data available in the filtered dataset.")
except Exception as e:
    st.error("Error generating skill inventory summary.")
    st.exception(e)

# -------------------------
# Export Options
st.header("💾 Export Options")
col_csv, col_pdf = st.columns(2)

with col_csv:
    if st.button("Export CSV"):
        try:
            display_df.to_csv("employee_records.csv", index=False)
            st.success("CSV exported successfully!")
        except Exception as e:
            st.error("Failed to export CSV.")
            st.exception(e)

with col_pdf:
    if st.button("Export PDF"):
        try:
            import io
            buffer = io.BytesIO()
            from utils import pdf_export
            pdf_export.generate_summary_pdf(
                buffer=buffer,
                total=summary["total"],
                active=summary["active"],
                resigned=summary["resigned"],
                df=display_df
            )
            st.download_button(
                "Download PDF",
                data=buffer,
                file_name="employee_records.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)
