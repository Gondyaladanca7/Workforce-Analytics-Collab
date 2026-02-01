# pages/7_Feedback.py
"""
Employee Feedback System (FINAL + PDF GRAPH FIXED)
- Clean feedback submission
- Role-based edit/delete
- Clear analytics
- Graph included in PDF export
"""

import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.analytics import feedback_summary
from utils.pdf_export import generate_master_report

# -------------------------
# Authentication
# -------------------------
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "unknown")
user_data = db.get_user_by_username(username)
user_id = user_data["id"] if user_data else None

st.title("💬 Employee Feedback System")

# -------------------------
# Load Employees and Feedback
# -------------------------
try:
    emp_df = db.fetch_employees()
except Exception:
    emp_df = pd.DataFrame(columns=["Emp_ID","Name","Status"])

try:
    feedback_df = db.fetch_feedback()
except Exception:
    feedback_df = pd.DataFrame(columns=["feedback_id","sender_id","receiver_id","message","rating","log_date"])

if emp_df.empty:
    st.info("No employee data available.")
if feedback_df.empty:
    st.info("No feedback available yet.")

# -------------------------
# Submit Feedback
# -------------------------
st.subheader("➕ Submit Feedback")

with st.form("add_feedback_form", clear_on_submit=True):
    receiver_options = (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist() if not emp_df.empty else []
    receiver = st.selectbox("Select Employee", receiver_options)
    message = st.text_area("Feedback Message")
    rating = st.slider("Rating (1 = Bad, 5 = Excellent)", 1, 5, 3)
    submit = st.form_submit_button("Submit Feedback")

    if submit:
        if not receiver or not message.strip():
            st.error("Please select employee and write feedback.")
        else:
            receiver_id = int(receiver.split(" - ")[0])
            try:
                db.add_feedback(user_id, receiver_id, message.strip(), rating)
                st.success("✅ Feedback submitted successfully.")
                st.rerun()
            except Exception as e:
                st.error("❌ Failed to submit feedback.")
                st.exception(e)

st.divider()

# -------------------------
# View Feedback
# -------------------------
st.subheader("📋 Feedback Records")

if not feedback_df.empty and not emp_df.empty:
    emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()

    feedback_df["Sender"] = feedback_df["sender_id"].map(emp_map).fillna("Anonymous")
    feedback_df["Receiver"] = feedback_df["receiver_id"].map(emp_map).fillna("Unknown")

    st.dataframe(
        feedback_df[["feedback_id","Sender","Receiver","message","rating","log_date"]],
        height=300,
        use_container_width=True
    )
else:
    st.info("No feedback to display.")

st.divider()

# -------------------------
# Edit / Delete Feedback
# -------------------------
st.subheader("✏️ Edit / Delete My Feedback")

editable_df = feedback_df.copy()

if role != "Admin" and user_id:
    editable_df = editable_df[editable_df["sender_id"] == user_id]

if editable_df.empty:
    st.info("No feedback available for editing.")
else:
    feedback_ids = editable_df["feedback_id"].astype(str).tolist()
    sel_id = st.selectbox("Select Feedback ID", feedback_ids)

    row = editable_df[editable_df["feedback_id"] == int(sel_id)].iloc[0]

    with st.form("edit_feedback_form"):
        new_msg = st.text_area("Message", value=row["message"])
        new_rating = st.slider("Rating", 1, 5, int(row["rating"]))
        update_btn = st.form_submit_button("Update")
        delete_btn = st.form_submit_button("Delete")

        if update_btn:
            try:
                db.update_feedback(int(sel_id), new_msg.strip(), new_rating)
                st.success("Feedback updated.")
                st.rerun()
            except Exception as e:
                st.error("Failed to update.")
                st.exception(e)

        if delete_btn:
            try:
                db.delete_feedback(int(sel_id))
                st.success("Feedback deleted.")
                st.rerun()
            except Exception as e:
                st.error("Failed to delete.")
                st.exception(e)

st.divider()

# -------------------------
# Feedback Analytics (GRAPH)
# -------------------------
st.subheader("📊 Feedback Analytics")

feedback_png = None  # for PDF

if not feedback_df.empty:
    summary_df = feedback_summary(feedback_df, emp_df)

    if not summary_df.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(summary_df["Employee"], summary_df["Avg_Rating"])

        ax.set_ylabel("Average Rating")
        ax.set_title("Average Feedback Rating per Employee")
        plt.xticks(rotation=45, ha="right")

        for bar in bars:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{bar.get_height():.1f}",
                ha="center",
                va="bottom"
            )

        plt.tight_layout()
        st.pyplot(fig)

        # ✅ convert to PNG for PDF
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        feedback_png = buf.read()
        plt.close(fig)

        st.dataframe(summary_df, use_container_width=True)
    else:
        st.info("No analytics data yet.")
else:
    st.info("No feedback data for analytics.")

# -------------------------
# Export Feedback PDF (WITH GRAPH)
# -------------------------
st.subheader("📄 Export Feedback Report")

if st.button("Generate Feedback PDF"):
    pdf_buffer = io.BytesIO()
    try:
        generate_master_report(
            buffer=pdf_buffer,
            employees_df=emp_df,
            notifications_df=feedback_df.rename(columns={"feedback_id": "id"}),
            notification_fig=feedback_png,  # ✅ GRAPH PASSED
            title="Employee Feedback Report"
        )
        pdf_buffer.seek(0)

        st.download_button(
            "Download PDF",
            pdf_buffer,
            "feedback_report.pdf",
            "application/pdf"
        )
    except Exception as e:
        st.error("Failed to generate PDF.")
        st.exception(e)
