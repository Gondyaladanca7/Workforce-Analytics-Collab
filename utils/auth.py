# utils/auth.py
"""
Authentication & Authorization utilities
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

    st.session_state.clear()
    st.session_state["logged_in"] = True
    st.session_state["user"]      = user["username"]
    st.session_state["role"]      = user["role"]
    st.session_state["user_id"]   = user["id"]

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
            submit   = st.form_submit_button("Login")

        if submit:
            success, msg = login(username, password)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

        st.stop()

    if roles_allowed:
        if st.session_state.get("role") not in roles_allowed:
            st.error("❌ Access denied for your role")
            st.stop()

# -------------------------
# Logout
# -------------------------
def logout_user():
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# -------------------------
# Role Badge (used by individual pages)
# Shows user + role + CSV import divider only on pages that call it
# -------------------------
def show_role_badge():
    role = st.session_state.get("role")
    user = st.session_state.get("user")

    if user:
        st.sidebar.markdown(f"👤 **User:** `{user}`")
    if role:
        st.sidebar.markdown(f"🧑‍💼 **Role:** `{role}`")

    # ── CSV Import shortcut on every page (Admin/HR) ──────────
    if role in ["Admin", "HR"]:
        st.sidebar.divider()
        st.sidebar.markdown("### 📥 Import CSV")

        import pandas as pd
        import datetime

        with st.sidebar.expander("Upload Employee CSV", expanded=False):
            st.caption("Columns: Name, Age, Gender, Department, Role, Skills, Join_Date, Status, Salary, Location")

            # Sample template download
            sample = pd.DataFrame({
                "Name":["Aarav Sharma","Priya Patel"],
                "Age":[28,32],
                "Gender":["Male","Female"],
                "Department":["IT","HR"],
                "Role":["Software Engineer","HR Manager"],
                "Skills":["Python:4;SQL:3","Recruitment:5;Excel:4"],
                "Join_Date":["2022-06-01","2021-03-15"],
                "Resign_Date":["",""],
                "Status":["Active","Active"],
                "Salary":[75000,65000],
                "Location":["Bangalore","Mumbai"],
            })
            st.download_button(
                "⬇️ Sample Template",
                sample.to_csv(index=False).encode("utf-8"),
                "employee_template.csv",
                "text/csv",
                use_container_width=True
            )

            uploaded = st.file_uploader("Choose CSV", type=["csv"], key="auth_csv_upload")

            if uploaded is not None:
                try:
                    csv_df = pd.read_csv(uploaded)
                    required = ["Name","Department","Role","Status"]
                    missing  = [c for c in required if c not in csv_df.columns]

                    if missing:
                        st.error(f"Missing columns: {missing}")
                    else:
                        # Fill defaults
                        for col, default in [("Age",30),("Gender","Male"),
                                             ("Skills","Excel:3"),
                                             ("Join_Date", datetime.date.today().strftime("%Y-%m-%d")),
                                             ("Resign_Date",""),("Salary",50000),("Location","Unknown")]:
                            if col not in csv_df.columns:
                                csv_df[col] = default
                            csv_df[col] = csv_df[col].fillna(default)

                        st.dataframe(csv_df.head(3), use_container_width=True)
                        st.caption(f"{len(csv_df)} rows ready to import")

                        if st.button("✅ Confirm Import", use_container_width=True, key="auth_confirm_import"):
                            ok = 0
                            for _, row in csv_df.iterrows():
                                try:
                                    db.add_employee({
                                        "Name":        str(row["Name"]),
                                        "Age":         int(row["Age"]),
                                        "Gender":      str(row["Gender"]),
                                        "Department":  str(row["Department"]),
                                        "Role":        str(row["Role"]),
                                        "Skills":      str(row["Skills"]),
                                        "Join_Date":   str(row["Join_Date"]),
                                        "Resign_Date": str(row["Resign_Date"]),
                                        "Status":      str(row["Status"]),
                                        "Salary":      float(row["Salary"]),
                                        "Location":    str(row["Location"]),
                                    })
                                    ok += 1
                                except Exception:
                                    pass
                            st.success(f"✅ {ok} employees imported!")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")