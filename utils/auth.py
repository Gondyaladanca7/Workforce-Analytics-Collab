import streamlit as st
from utils import database as db
import hashlib

# -------------------------
# Password Hashing
# -------------------------
def hash_password(password: str) -> str:
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

    if hash_password(password) != user["password"]:
        return False, "Invalid password"

    # -------------------------
    # Session State (FIXED)
    # -------------------------
    st.session_state.clear()  # 🔥 avoid stale values

    st.session_state["logged_in"] = True
    st.session_state["user"] = user["username"]
    st.session_state["role"] = user["role"]
    st.session_state["user_id"] = user["id"]

    # -------------------------
    # Employee ID mapping (CRITICAL FIX)
    # -------------------------
    emp_id = None
    try:
        emp_id = db.get_emp_id_by_user_id(user["id"])
    except Exception:
        pass

    st.session_state["my_emp_id"] = emp_id

    return True, "Login successful"


# -------------------------
# Require Login
# -------------------------
def require_login(roles_allowed=None):
    if not st.session_state.get("logged_in"):
        st.warning("⚠️ Please login to continue")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            success, msg = login(username, password)
            if success:
                st.success(msg)
                st.experimental_rerun()
            else:
                st.error(msg)

        st.stop()

    if roles_allowed and st.session_state.get("role") not in roles_allowed:
        st.error("❌ Access denied")
        st.stop()


# -------------------------
# Logout
# -------------------------
def logout_user():
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()


# -------------------------
# Role Badge
# -------------------------
def show_role_badge():
    role = st.session_state.get("role")
    if role:
        st.sidebar.markdown(f"### 🧑‍💼 Role: `{role}`")
