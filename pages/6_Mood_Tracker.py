# pages/6_Mood_Tracker.py
"""
Employee Mood Tracker — Workforce Analytics System
Log employee mood, view history, visualize trends, and export PDF reports.
"""

import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import io

from utils import database as db
from utils.pdf_export import generate_master_report  # ✅ use updated PDF generator
from utils.auth import require_login, show_role_badge, logout_user

st.set_page_config(page_title="Mood Tracker", page_icon="😊", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "unknown")

st.title("😊 Employee Mood Tracker")

# -------------------------
# Fetch Employees
# -------------------------
try:
    employees_df = db.fetch_employees()
except Exception:
    employees_df = pd.DataFrame(columns=["Emp_ID", "Name", "Status"])

# Role-based employee visibility
if role not in ["Admin", "Manager"]:
    employees_df = employees_df[employees_df["Name"] == username]

emp_list = []
if not employees_df.empty:
    emp_list = (employees_df["Emp_ID"].astype(str) + " - " + employees_df["Name"]).tolist()

emp_choice = st.selectbox("Select Employee", options=emp_list)
emp_id = int(emp_choice.split(" - ")[0]) if emp_choice else None

# -------------------------
# Log Mood (FORM)
# -------------------------
with st.form("log_mood_form", clear_on_submit=True):
    mood_choice = st.radio(
        "Today's Mood", ["😊 Happy", "😐 Neutral", "😔 Sad", "😡 Angry"], horizontal=True
    )
    remarks = st.text_input("Optional remarks")
    submit_mood = st.form_submit_button("Log Mood")

    if submit_mood:
        if emp_id:
            try:
                db.add_mood_entry(emp_id=emp_id, mood=mood_choice, remarks=remarks or "")
                st.success(f"Mood '{mood_choice}' logged for {emp_choice.split(' - ')[1]}")
                st.rerun()
            except Exception as e:
                st.error("❌ Failed to log mood.")
                st.exception(e)
        else:
            st.warning("Select an employee first.")

st.markdown("---")

# -------------------------
# View Mood History
# -------------------------
st.subheader("📋 Mood History")
try:
    mood_df = db.fetch_mood_logs()
    if not mood_df.empty and not employees_df.empty:
        emp_map = employees_df.set_index("Emp_ID")["Name"].to_dict()
        mood_df["Employee"] = mood_df["emp_id"].map(emp_map).fillna(mood_df["emp_id"].astype(str))
        mood_df["log_date_parsed"] = pd.to_datetime(mood_df["log_date"], errors="coerce")
        mood_df_sorted = mood_df.sort_values("log_date_parsed", ascending=False)
        st.dataframe(
            mood_df_sorted[["Employee","mood","remarks","log_date_parsed"]].rename(columns={"log_date_parsed":"log_date"}),
            height=360
        )
except Exception as e:
    st.error("❌ Failed to fetch mood history.")
    st.exception(e)

# -------------------------
# Mood Analytics
# -------------------------
st.subheader("📊 Mood Analytics")
if not mood_df.empty:
    fig, ax = plt.subplots(figsize=(5,5))
    mood_counts = mood_df["mood"].value_counts()
    ax.pie(mood_counts.values, labels=mood_counts.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("Overall Mood Distribution")
    st.pyplot(fig)

    fig2, ax2 = plt.subplots(figsize=(8,4))
    mood_time = mood_df.groupby([pd.Grouper(key="log_date_parsed", freq="W"), "mood"]).size().unstack(fill_value=0)
    mood_time.plot(kind="bar", stacked=True, ax=ax2)
    ax2.set_title("Weekly Mood Trends")
    ax2.set_xlabel("Week")
    ax2.set_ylabel("Count")
    st.pyplot(fig2)

# -------------------------
# Export Mood PDF
# -------------------------
st.subheader("📄 Export Mood Logs as PDF")
pdf_buffer = io.BytesIO()
with st.form("generate_mood_pdf"):
    submit_pdf = st.form_submit_button("Generate Mood PDF")
    if submit_pdf:
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=employees_df,
                mood_df=mood_df,
                title="Employee Mood Summary Report"
            )
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="mood_summary_report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error("❌ Failed to generate PDF.")
            st.exception(e)
