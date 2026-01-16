import streamlit as st
from utils import database as db
import hashlib

# -------------------------
# Password Hashing
# -------------------------
def hash_password(password: str) -> str:
    """Return SHA256 hash of the password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# -------------------------
# Login Logic
# -------------------------
def login(username: str, password: str):
    """Validate user and setup session_state."""
    try:
        user = db.get_user_by_username(username)
    except Exception as e:
        return False, f"DB error: {e}"

    if not user:
        return False, "User not found"

    if hash_password(password) != user.get("password", ""):
        return False, "Invalid password"

    # Clear old session safely
    st.session_state.clear()

    # Set session variables
    st.session_state["logged_in"] = True
    st.session_state["user"] = user.get("username", "unknown")
    st.session_state["role"] = user.get("role", "Employee")
    st.session_state["user_id"] = user.get("id")

    # Employee ID mapping
    emp_id = None
    try:
        emp_id = db.get_emp_id_by_user_id(user.get("id"))
    except Exception:
        pass
    st.session_state["my_emp_id"] = emp_id

    return True, "Login successful"


# -------------------------
# Require Login
# -------------------------
def require_login(roles_allowed=None):
    """
    Ensure the user is logged in and optionally has allowed roles.
    Use this at the start of each page.
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

    # Role check
    if roles_allowed and st.session_state.get("role") not in roles_allowed:
        st.error("❌ Access denied for your role")
        st.stop()


# -------------------------
# Logout
# -------------------------
def logout_user():
    """Button in sidebar to logout user."""
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()


# -------------------------
# Role Badge & Username
# -------------------------
def show_role_badge():
    """Display role and username in sidebar."""
    role = st.session_state.get("role")
    user = st.session_state.get("user")
    if role:
        st.sidebar.markdown(f"### 🧑‍💼 Role: `{role}`")
    if user:
        st.sidebar.markdown(f"### 👤 User: `{user}`")
