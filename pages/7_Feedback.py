import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_summary_pdf
from utils.analytics import feedback_summary

def show():
    require_login()
    show_role_badge()
    logout_user()

    role = st.session_state.get("role", "Employee")
    username = st.session_state.get("user", "unknown")

    st.title("💬 Employee Feedback System")

    # -------------------------
    # Load Employees and Feedback
    # -------------------------
    try:
        emp_df = db.fetch_employees()
    except Exception:
        emp_df = pd.DataFrame()

    try:
        feedback_df = db.fetch_feedback()
    except Exception:
        feedback_df = pd.DataFrame()

    # -------------------------
    # Add Feedback
    # -------------------------
    st.subheader("➕ Submit Feedback")
    with st.form("add_feedback", clear_on_submit=True):
        receiver_options = (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist() if not emp_df.empty else []
        receiver = st.selectbox("Select Employee to Give Feedback", receiver_options)
        message = st.text_area("Message")
        rating = st.slider("Rating (1-5)", min_value=1, max_value=5, value=5)
        anonymous = st.checkbox("Submit Anonymously")
        submit = st.form_submit_button("Submit Feedback")
        if submit:
            if not receiver or not message.strip():
                st.error("Please select a receiver and write a message.")
            else:
                receiver_id = int(receiver.split(" - ")[0])
                sender_user = db.get_user_by_username(username) if not anonymous else {"id": None}
                sender_id = sender_user["id"] if sender_user else None
                try:
                    db.add_feedback(sender_id, receiver_id, message.strip(), rating)
                    st.success("Feedback submitted successfully.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error("Failed to submit feedback.")
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
    if not feedback_display.empty:
        st.subheader("✏️ Edit / Delete Feedback")
        editable_feedback = feedback_display.copy()
        if role != "Admin":
            editable_feedback = editable_feedback[editable_feedback["Sender"]==username]

        feedback_ids = editable_feedback["feedback_id"].astype(str).tolist()
        if feedback_ids:
            sel_feedback = st.selectbox("Select Feedback ID", feedback_ids)
            feedback_row = editable_feedback[editable_feedback["feedback_id"] == int(sel_feedback)].iloc[0].to_dict()

            with st.form("edit_feedback"):
                e_message = st.text_area("Message", value=feedback_row.get("message",""))
                e_rating = st.slider("Rating (1-5)", min_value=1, max_value=5, value=int(feedback_row.get("rating",5)))
                update_btn = st.form_submit_button("Update Feedback")
                delete_btn = st.form_submit_button("Delete Feedback")

                if update_btn:
                    try:
                        db.add_feedback(feedback_row["sender_id"], feedback_row["receiver_id"], e_message.strip(), e_rating)
                        db.delete_feedback(int(sel_feedback))
                        st.success("Feedback updated successfully.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error("Failed to update feedback.")
                        st.exception(e)

                if delete_btn:
                    try:
                        db.delete_feedback(int(sel_feedback))
                        st.success("Feedback deleted successfully.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error("Failed to delete feedback.")
                        st.exception(e)

    st.markdown("---")

    # -------------------------
    # Feedback Analytics
    # -------------------------
    st.subheader("📊 Feedback Analytics")
    if not feedback_df.empty:
        summary_df = feedback_summary(feedback_df, emp_df)
        st.bar_chart(summary_df.set_index("Employee")["Avg_Rating"])
        st.write(summary_df)
    else:
        st.info("No feedback available yet.")

    # -------------------------
    # Export Feedback PDF
    # -------------------------
    st.subheader("📄 Export Feedback PDF")
    pdf_buffer = io.BytesIO()
    if st.button("Generate Feedback PDF"):
        try:
            generate_summary_pdf(
                buffer=pdf_buffer,
                total=len(emp_df),
                active=len(emp_df[emp_df["Status"]=="Active"]) if "Status" in emp_df.columns else len(emp_df),
                resigned=len(emp_df[emp_df["Status"]=="Resigned"]) if "Status" in emp_df.columns else 0,
                df=emp_df,
                mood_df=None,
                title="Employee Feedback Report"
            )
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="feedback_report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)
