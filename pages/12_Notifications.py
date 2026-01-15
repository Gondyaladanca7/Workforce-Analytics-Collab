# pages/12_Notifications.py
import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt
from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_summary_pdf

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
        st.metric("Total", len(filtered))
    with col2:
        st.metric("Unread", (filtered["is_read"] == 0).sum())

    # Notifications by type
    type_counts = filtered["type"].value_counts()
    fig_type, ax_type = plt.subplots()
    type_counts.plot(kind="bar", ax=ax_type, color="skyblue")
    ax_type.set_ylabel("Count")
    ax_type.set_title("Notifications by Type")
    st.pyplot(fig_type, use_container_width=True)
    plt.close(fig_type)

    # -------------------------
    # Export PDF
    # -------------------------
    st.subheader("📄 Export Notifications PDF")
    pdf_buffer = io.BytesIO()
    if st.button("Generate Notifications PDF"):
        try:
            import matplotlib.pyplot as plt

            # Notifications by Type Chart
            fig_type, ax1 = plt.subplots(figsize=(6,3))
            type_counts.plot(kind="bar", ax=ax1, color="skyblue")
            ax1.set_ylabel("Count")
            ax1.set_title("Notifications by Type")

            # Notifications by Status Chart
            status_counts = filtered["is_read"].map({0:"Unread",1:"Read"}).value_counts()
            fig_status, ax2 = plt.subplots(figsize=(6,3))
            status_counts.plot(kind="bar", ax=ax2, color="orange")
            ax2.set_ylabel("Count")
            ax2.set_title("Notifications by Status")

            # Generate PDF
            generate_summary_pdf(
                buffer=pdf_buffer,
                total=len(filtered),
                active=(filtered["is_read"]==0).sum(),
                resigned=(filtered["is_read"]==1).sum(),
                df=filtered,
                mood_df=None,
                dept_fig=fig_type,
                gender_fig=fig_status,
                salary_fig=None,
                title="Notifications Report"
            )

            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="notifications_report.pdf",
                mime="application/pdf"
            )

            # Close figures
            plt.close(fig_type)
            plt.close(fig_status)

        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)
