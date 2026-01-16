# pages/7_Feedback.py
"""
Employee Feedback System — Workforce Analytics System
Submit feedback, view history, analyze ratings, and export PDF reports.
"""

import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report
from utils.analytics import feedback_summary

def show():
    # -------------------------
    # Authentication
    # -------------------------
    require_login()
    show_role_badge()
    logout_user()

    role = st.session_state.get("role", "Employee")
    username = st.session_state.get("user", "unknown")
    user_id = db.get_user_by_username(username)["id"] if db.get_user_by_username(username) else None

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

    # -------------------------
    # Submit Feedback (FORM)
    # -------------------------
    st.subheader("➕ Submit Feedback")
    with st.form("add_feedback_form", clear_on_submit=True):
        receiver_options = (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist() if not emp_df.empty else []
        receiver = st.selectbox("Select Employee to Give Feedback", receiver_options)
        message = st.text_area("Message")
        rating = st.slider("Rating (1-5)", min_value=1, max_value=5, value=5)
        anonymous = st.checkbox("Submit Anonymously")
        submit_feedback = st.form_submit_button("Submit Feedback")

        if submit_feedback:
            if not receiver or not message.strip():
                st.error("Please select a receiver and write a message.")
            else:
                receiver_id = int(receiver.split(" - ")[0])
                sender_id = None if anonymous else user_id
                try:
                    db.add_feedback(sender_id, receiver_id, message.strip(), rating)
                    # ✅ Safe refresh without rerun
                    feedback_df = db.fetch_feedback()
                    st.success("✅ Feedback submitted successfully.")
                except Exception as e:
                    st.error("❌ Failed to submit feedback.")
                    st.exception(e)

    st.markdown("---")

    # -------------------------
    # View & Filter Feedback
    # -------------------------
    st.subheader("🔎 View Feedback")
    search_text = st.text_input("Search (message, sender, receiver)").lower().strip()
    feedback_display = feedback_df.copy()

    if not feedback_display.empty and not emp_df.empty:
        emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()
        feedback_display["Sender"] = feedback_display["sender_id"].map(emp_map).fillna("Anonymous")
        feedback_display["Receiver"] = feedback_display["receiver_id"].map(emp_map).fillna(feedback_display["receiver_id"].astype(str))

        if search_text:
            mask = (
                feedback_display["message"].str.lower().str.contains(search_text, na=False) |
                feedback_display["Sender"].str.lower().str.contains(search_text, na=False) |
                feedback_display["Receiver"].str.lower().str.contains(search_text, na=False)
            )
            feedback_display = feedback_display[mask]

    st.dataframe(
        feedback_display[["feedback_id","Sender","Receiver","message","rating","log_date"]],
        height=300
    )

    st.markdown("---")

    # -------------------------
    # Edit / Delete Feedback
    # -------------------------
    st.subheader("✏️ Edit / Delete Feedback")
    editable_feedback = feedback_display.copy()
    if role != "Admin":
        editable_feedback = editable_feedback[editable_feedback["sender_id"] == user_id]

    if not editable_feedback.empty:
        feedback_ids = editable_feedback["feedback_id"].astype(str).tolist()
        sel_feedback = st.selectbox("Select Feedback ID", feedback_ids)
        feedback_row = editable_feedback[editable_feedback["feedback_id"] == int(sel_feedback)].iloc[0].to_dict()

        with st.form("edit_feedback_form"):
            e_message = st.text_area("Message", value=feedback_row.get("message",""))
            e_rating = st.slider("Rating (1-5)", min_value=1, max_value=5, value=int(feedback_row.get("rating",5)))
            update_btn = st.form_submit_button("Update Feedback")
            delete_btn = st.form_submit_button("Delete Feedback")

            if update_btn:
                try:
                    db.update_feedback(int(sel_feedback), e_message.strip(), e_rating)
                    # ✅ Safe refresh
                    feedback_df = db.fetch_feedback()
                    st.success("✅ Feedback updated successfully.")
                except Exception as e:
                    st.error("❌ Failed to update feedback.")
                    st.exception(e)

            if delete_btn:
                try:
                    db.delete_feedback(int(sel_feedback))
                    # ✅ Safe refresh
                    feedback_df = db.fetch_feedback()
                    st.success("✅ Feedback deleted successfully.")
                except Exception as e:
                    st.error("❌ Failed to delete feedback.")
                    st.exception(e)

    st.markdown("---")

    # -------------------------
    # Feedback Analytics
    # -------------------------
    st.subheader("📊 Feedback Analytics")
    if not feedback_df.empty:
        summary_df = feedback_summary(feedback_df, emp_df)
        if not summary_df.empty:
            st.bar_chart(summary_df.set_index("Employee")["Avg_Rating"])
            st.dataframe(summary_df)
        else:
            st.info("No feedback summary available yet.")
    else:
        st.info("No feedback available yet.")

    # -------------------------
    # Export Feedback PDF
    # -------------------------
    st.subheader("📄 Export Feedback PDF")
    pdf_buffer = io.BytesIO()
    with st.form("generate_feedback_pdf"):
        submit_pdf = st.form_submit_button("Generate Feedback PDF")
        if submit_pdf:
            try:
                generate_master_report(
                    buffer=pdf_buffer,
                    employees_df=emp_df,
                    notifications_df=feedback_df.rename(columns={"feedback_id":"id"}),
                    title="Employee Feedback Summary Report"
                )
                st.download_button(
                    label="Download PDF",
                    data=pdf_buffer,
                    file_name="feedback_report.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error("❌ Failed to generate PDF.")
                st.exception(e)
# -------------------------
# Import CSV (Admin Only)
# -------------------------
if role in ["Admin", "Manager", "HR"]:
    st.sidebar.subheader("📥 Import Attendance CSV")
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        try:
            df_csv = pd.read_csv(uploaded_file)
            # Validate required columns
            required_cols = ["emp_id","date","check_in","check_out","status"]
            if all(col in df_csv.columns for col in required_cols):
                db.bulk_add_attendance(df_csv)  # You need to create this in db.py
                st.success("✅ Attendance imported successfully!")
            else:
                st.error(f"CSV missing required columns: {required_cols}")
        except Exception as e:
            st.error("❌ Failed to import CSV")
            st.exception(e)
