# utils/auth.py

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
# Login
# -------------------------
def login(username: str, password: str):
    try:
        user = db.get_user_by_username(username)
    except Exception as e:
        return False, f"DB error: {e}"

    if not user:
        return False, "User not found"

    stored_hash = user.get("password")
    input_hash = hash_password(password)

    if input_hash != stored_hash:
        return False, "Invalid password"

    # Store session info
    st.session_state["logged_in"] = True
    st.session_state["user"] = user["username"]
    st.session_state["role"] = user["role"]
    st.session_state["user_id"] = user["id"]

    # Optional: link username to Emp_ID
    try:
        employees = db.fetch_employees()
        emp_row = employees[employees["Name"] == username]
        if not emp_row.empty:
            st.session_state["my_emp_id"] = int(emp_row.iloc[0]["Emp_ID"])
        else:
            st.session_state["my_emp_id"] = None
    except Exception:
        st.session_state["my_emp_id"] = None

    return True, "Login successful"


# -------------------------
# Require login decorator
# -------------------------
def require_login(roles_allowed=None):
    """
    Enforce login and optionally role-based access.
    roles_allowed: list of roles, e.g., ["Admin","Manager"]
    """
    if not st.session_state.get("logged_in", False):
        st.warning("⚠️ Please login to continue")

        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login", key="login_btn"):
            success, msg = login(username, password)
            if success:
                st.success(msg)
            else:
                st.error(msg)

        st.stop()

    # Role enforcement
    if roles_allowed and st.session_state.get("role") not in roles_allowed:
        st.error("❌ Access denied. Your role cannot access this page.")
        st.stop()


# -------------------------
# Logout
# -------------------------
def logout_user():
    """
    Logout button for sidebar. Clears session_state keys.
    Only place this in app.py sidebar to avoid duplicates.
    """
    if st.sidebar.button("Logout", key="logout_btn"):
        keys_to_clear = [
            "logged_in", "user", "role", "user_id", "my_emp_id"
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.success("Logged out successfully")
        st.experimental_set_query_params()


# -------------------------
# Role Badge Display
# -------------------------
def show_role_badge():
    role = st.session_state.get("role", "")
    if role:
        st.sidebar.markdown(f"### 🧑‍💼 Role: `{role}`")
