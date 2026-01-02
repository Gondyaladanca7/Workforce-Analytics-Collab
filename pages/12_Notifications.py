# pages/12_Notifications.py

import streamlit as st
import pandas as pd

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db


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
        type_filter = st.selectbox(
            "Type",
            ["All", "Task", "Feedback", "Mood", "Attendance"]
        )

    filtered = notif_df.copy()

    if status_filter != "All":
        filtered = filtered[
            filtered["is_read"] == (1 if status_filter == "Read" else 0)
        ]

    if type_filter != "All":
        filtered = filtered[filtered["type"] == type_filter]

    filtered = filtered.sort_values("created_at", ascending=False)

    # -----------------------
    # Display Notifications
    # -----------------------
    for _, row in filtered.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([6, 1, 1])

            with c1:
                st.markdown(
                    f"""
                    **{row['title']}**  
                    {row['message']}  
                    <small>{row['created_at']}</small>
                    """,
                    unsafe_allow_html=True
                )

            with c2:
                if row["is_read"] == 0:
                    if st.button("✔ Read", key=f"read_{row['id']}"):
                        db.mark_notification_read(row["id"])
                        st.experimental_rerun()
                else:
                    st.caption("Read")

            with c3:
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
