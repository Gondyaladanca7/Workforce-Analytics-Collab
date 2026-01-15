# pages/12_Notifications.py

import streamlit as st
import pandas as pd
import io
from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_summary_pdf
import matplotlib.pyplot as plt

def show():
    require_login()
    show_role_badge()
    logout_user()

    role = st.session_state.get("role", "Employee")
    username = st.session_state.get("user")

    st.title("🔔 Notifications Center")

    # -----------------------
    # Load Notifications
    # -----------------------
    try:
        notif_df = db.fetch_notifications(username=username, role=role)
    except Exception as e:
        st.error("Failed to load notifications.")
        st.exception(e)
        return

    if notif_df.empty:
        st.info("No notifications available.")
        return

    # -----------------------
    # Filters
    # -----------------------
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Status", ["All", "Unread", "Read"])
    with col2:
        type_filter = st.selectbox("Type", ["All", "Task", "Feedback", "Mood", "Attendance"])

    filtered = notif_df.copy()
    if status_filter != "All":
        filtered = filtered[filtered["is_read"] == (1 if status_filter == "Read" else 0)]
    if type_filter != "All":
        filtered = filtered[filtered["type"] == type_filter]

    filtered = filtered.sort_values("created_at", ascending=False)

    # -----------------------
    # Display Notifications
    # -----------------------
    for _, row in filtered.iterrows():
        bg_color = "#FFFACD" if row["is_read"] == 0 else "white"
        with st.container():
            st.markdown(
                f"""
                <div style="padding:10px; background-color:{bg_color}; border-radius:5px; margin-bottom:5px;">
                    <strong>{row['title']}</strong>  <br>
                    {row['message']} <br>
                    <small>{row['created_at']}</small>
                </div>
                """,
                unsafe_allow_html=True
            )
            c1, c2 = st.columns([1,1])
            with c1:
                if row["is_read"] == 0 and st.button("✔ Read", key=f"read_{row['id']}"):
                    db.mark_notification_read(row["id"])
                    st.experimental_rerun()
            with c2:
                if st.button("🗑", key=f"del_{row['id']}"):
                    db.delete_notification(row["id"])
                    st.experimental_rerun()

    st.markdown("---")

    # -----------------------
    # Analytics
    # -----------------------
    st.subheader("📊 Notification Analytics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total", len(notif_df))
    with col2:
        st.metric("Unread", (notif_df["is_read"] == 0).sum())

    # Notifications by type
    type_counts = notif_df["type"].value_counts()
    fig, ax = plt.subplots()
    type_counts.plot(kind="bar", ax=ax, color="skyblue")
    ax.set_ylabel("Count")
    ax.set_title("Notifications by Type")
    st.pyplot(fig, use_container_width=True)

    # -----------------------
    # Export PDF
    # -----------------------
    st.subheader("📄 Export Notifications PDF")
    pdf_buffer = io.BytesIO()
    if st.button("Generate Notifications PDF"):
        try:
            generate_summary_pdf(
                buffer=pdf_buffer,
                total=len(notif_df),
                active=(notif_df["is_read"] == 0).sum(),
                resigned=(notif_df["is_read"] == 1).sum(),
                df=notif_df,
                mood_df=None,
                title="Notifications Report"
            )
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="notifications_report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)
