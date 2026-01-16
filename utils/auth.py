# utils/auth.py
"""
Authentication & Authorization utilities
Workforce Intelligence System
"""

import streamlit as st
import hashlib
from utils import database as db

# -------------------------
# Password Hashing
# -------------------------
def hash_password(password: str) -> str:
    """
    Return SHA256 hash of the password.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# -------------------------
# Login Logic
# -------------------------
def login(username: str, password: str):
    """
    Validate user credentials and initialize session state.
    """
    try:
        user = db.get_user_by_username(username)
    except Exception as e:
        return False, f"Database error: {e}"

    if not user:
        return False, "User not found"

    if hash_password(password) != user.get("password"):
        return False, "Invalid password"

    # Clear any previous session data
    st.session_state.clear()

    # Set session variables
    st.session_state["logged_in"] = True
    st.session_state["user"] = user.get("username")
    st.session_state["role"] = user.get("role")
    st.session_state["user_id"] = user.get("id")

    # Map user → employee safely
    emp_id = None
    try:
        emp_id = db.get_emp_id_by_user_id(user.get("id"))
    except Exception:
        emp_id = None

    st.session_state["my_emp_id"] = emp_id

    return True, "Login successful"


# -------------------------
# Require Login (Guard)
# -------------------------
def require_login(roles_allowed=None):
    """
    Ensures user is logged in.
    Optionally restricts access to specific roles.
    """
    if not st.session_state.get("logged_in"):
        st.warning("⚠️ Please login to continue")

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            success, msg = login(username, password)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

        st.stop()

    # Role-based access control
    if roles_allowed:
        if st.session_state.get("role") not in roles_allowed:
            st.error("❌ Access denied for your role")
            st.stop()


# -------------------------
# Logout
# -------------------------
def logout_user():
    """
    Logout button (sidebar).
    Clears session safely.
    """
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()


# -------------------------
# Role Badge (Sidebar)
# -------------------------
def show_role_badge():
    """
    Displays logged-in user and role in sidebar.
    """
    role = st.session_state.get("role")
    user = st.session_state.get("user")

    if role:
        st.sidebar.markdown(f"### 🧑‍💼 Role: `{role}`")
    if user:
        st.sidebar.markdown(f"### 👤 User: `{user}`")
