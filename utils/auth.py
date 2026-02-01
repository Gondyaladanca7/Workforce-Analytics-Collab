# utils/auth.py
"""
Authentication & Authorization utilities (FIXED)
- Secure password hashing
- Clean role-based access control
- Safe session handling
"""

import streamlit as st
import hashlib
from utils import database as db

# -------------------------
# Password Hashing
# -------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# -------------------------
# Login Logic
# -------------------------
def login(username: str, password: str):
    try:
        user = db.get_user_by_username(username)
    except Exception as e:
        return False, f"Database error: {e}"

    if not user:
        return False, "User not found"

    hashed_input = hash_password(password)

    if hashed_input != user["password"]:
        return False, "Invalid password"

    # Reset session safely
    st.session_state.clear()

    st.session_state["logged_in"] = True
    st.session_state["user"] = user["username"]
    st.session_state["role"] = user["role"]
    st.session_state["user_id"] = user["id"]

    return True, "Login successful"

# -------------------------
# Require Login (Guard)
# -------------------------
def require_login(roles_allowed=None):
    if not st.session_state.get("logged_in"):
        st.warning("⚠️ Please login to continue")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

        if submit:
            success, msg = login(username, password)
            if success:
                st.success(msg)
                st.rerun()

            else:
                st.error(msg)

        st.stop()

    # Role restriction
    if roles_allowed:
        if st.session_state.get("role") not in roles_allowed:
            st.error("❌ Access denied for your role")
            st.stop()

# -------------------------
# Logout
# -------------------------
def logout_user():
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()


# -------------------------
# Role Badge
# -------------------------
def show_role_badge():
    role = st.session_state.get("role")
    user = st.session_state.get("user")

    if user:
        st.sidebar.markdown(f"👤 **User:** `{user}`")
    if role:
        st.sidebar.markdown(f"🧑‍💼 **Role:** `{role}`")
