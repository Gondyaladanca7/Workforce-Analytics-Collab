# pages/6_Mood_Tracker.py
"""
Employee Mood Tracker — Survey Based (FIXED)
Uses 5-question survey and calculates mood automatically.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from utils import database as db
from utils.auth import require_login, show_role_badge, logout_user

st.set_page_config(page_title="Mood Tracker", page_icon="😊", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "unknown")

st.title("😊 Employee Mood Survey")

# -------------------------
# Fetch Employees
# -------------------------
try:
    employees_df = db.fetch_employees()
except Exception:
    employees_df = pd.DataFrame(columns=["Emp_ID", "Name", "Status"])

if employees_df.empty:
    st.info("No employee data available.")
    st.stop()

# Role-based visibility
if role not in ["Admin", "Manager", "HR"]:
    employees_df = employees_df[employees_df["Name"] == username]

emp_list = (employees_df["Emp_ID"].astype(str) + " - " + employees_df["Name"]).tolist()
emp_choice = st.selectbox("Select Employee", emp_list)
emp_id = int(emp_choice.split(" - ")[0])

# -------------------------
# Mood Survey Form
# -------------------------
st.subheader("📝 Daily Mood Survey (1 = Worst, 5 = Best)")

with st.form("mood_survey_form", clear_on_submit=True):
    q1 = st.slider("1️⃣ How stressed do you feel today?", 1, 5, 3)
    q2 = st.slider("2️⃣ How satisfied are you with your work today?", 1, 5, 3)
    q3 = st.slider("3️⃣ How motivated do you feel today?", 1, 5, 3)
    q4 = st.slider("4️⃣ How is your work-life balance today?", 1, 5, 3)
    q5 = st.slider("5️⃣ How supportive is your team today?", 1, 5, 3)

    remarks = st.text_input("Optional remarks")
    submit = st.form_submit_button("Submit Survey")

    if submit:
        total_score = q1 + q2 + q3 + q4 + q5

        if total_score >= 20:
            mood_label = "😊 Happy"
        elif total_score >= 13:
            mood_label = "😐 Neutral"
        else:
            mood_label = "😟 Stressed"

        try:
            db.add_mood_entry(
                emp_id=emp_id,
                mood_score=int(total_score),
                remarks=f"{mood_label} | {remarks}"
            )
            st.success(f"Mood recorded: {mood_label} (Score: {total_score}/25)")
            st.rerun()

        except Exception as e:
            st.error("❌ Failed to save mood survey.")
            st.exception(e)

st.markdown("---")

# -------------------------
# View Mood History
# -------------------------
st.subheader("📋 Mood History")

try:
    mood_df = db.fetch_mood_logs()
except Exception:
    mood_df = pd.DataFrame(columns=["emp_id","mood_score","remarks","log_date"])

if not mood_df.empty:
    emp_map = employees_df.set_index("Emp_ID")["Name"].to_dict()
    mood_df["Employee"] = mood_df["emp_id"].map(emp_map).fillna(mood_df["emp_id"].astype(str))

    mood_df["Score"] = pd.to_numeric(mood_df["mood_score"], errors="coerce")
    mood_df["Date"] = pd.to_datetime(mood_df["log_date"], errors="coerce")

    mood_df["Mood"] = mood_df["Score"].apply(
        lambda x: "😊 Happy" if x >= 20 else ("😐 Neutral" if x >= 13 else "😟 Stressed")
    )

    mood_df_sorted = mood_df.sort_values("Date", ascending=False)

    st.dataframe(
        mood_df_sorted[["Employee","Mood","Score","remarks","Date"]],
        height=350,
        use_container_width=True
    )

    # -------------------------
    # Mood Analytics
    # -------------------------
    st.subheader("📊 Mood Analytics")

    mood_counts = mood_df["Mood"].value_counts()

    fig, ax = plt.subplots()
    bars = ax.bar(mood_counts.index, mood_counts.values)
    ax.set_title("Mood Distribution")
    ax.set_ylabel("Count")

    # show numbers on bars
    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(int(bar.get_height())),
            ha="center",
            va="bottom"
        )

    st.pyplot(fig)

else:
    st.info("No mood survey data available yet.")
