# pages/15_AI_Summary.py
"""
AI Attrition & Workforce Summary — Workforce Intelligence System
- AI-generated report on why employees are leaving or at risk
- Attrition risk scoring per employee
- Department-level turnover analysis
- Mood + Attendance + Feedback correlation
- Exportable PDF report with AI insights
- Powered by Claude AI
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import io
from datetime import datetime, date

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -------------------------
# Page Config & Auth
# -------------------------
st.set_page_config(page_title="AI Summary", page_icon="🧠", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "Unknown")

if role not in ["Admin", "HR", "Manager"]:
    st.warning("⚠️ Access denied. Admin, HR and Manager only.")
    st.stop()

st.title("🧠 AI Workforce Summary & Attrition Analysis")
st.caption("AI-generated insights on employee turnover, risk factors, and retention strategies")

# -------------------------
# API Key (Sidebar)
# -------------------------
st.sidebar.header("🔑 AI Configuration")
api_key = st.sidebar.text_input(
    "Anthropic API Key",
    type="password",
    placeholder="sk-ant-...",
    help="Get your key at console.anthropic.com"
)

ai_model = st.sidebar.selectbox(
    "AI Model",
    ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    index=0
)

# -------------------------
# Load All Data
# -------------------------
@st.cache_data(ttl=60)
def load_data():
    try:
        emp = db.fetch_employees()
        att = db.fetch_attendance()
        mood = db.fetch_mood_logs()
        tasks = db.fetch_tasks()
        feedback = db.fetch_feedback()
        projects = db.fetch_projects()
        return emp, att, mood, tasks, feedback, projects
    except Exception as e:
        return (pd.DataFrame(),) * 6

emp_df, att_df, mood_df, tasks_df, feedback_df, projects_df = load_data()

if emp_df.empty:
    st.error("No employee data found. Please add employees first.")
    st.stop()

# -------------------------
# ATTRITION RISK SCORING ENGINE
# -------------------------
def compute_attrition_risk(emp_df, att_df, mood_df, feedback_df, tasks_df):
    """
    Score each employee 0-100 for attrition risk based on:
    - Attendance irregularity (+30)
    - Low mood / stress (+30)
    - Low feedback rating (+20)
    - Already resigned (flag)
    - Long tenure with no growth (estimated, +10)
    - High task overdue rate (+10)
    """
    results = []

    for _, emp in emp_df.iterrows():
        eid = emp["Emp_ID"]
        risk = 0
        factors = []

        # Already resigned
        if emp.get("Status") == "Resigned":
            results.append({
                "Emp_ID": eid,
                "Name": emp["Name"],
                "Department": emp["Department"],
                "Role": emp["Role"],
                "Status": emp["Status"],
                "Risk_Score": 100,
                "Risk_Level": "🔴 Resigned",
                "Key_Factors": "Employee has already resigned"
            })
            continue

        # --- Attendance Risk ---
        emp_att = att_df[att_df["emp_id"] == eid] if not att_df.empty else pd.DataFrame()
        if not emp_att.empty:
            absent_count = len(emp_att[emp_att["status"].str.lower().isin(["absent", "half-day"])])
            total_att = len(emp_att)
            absent_rate = absent_count / total_att if total_att > 0 else 0
            if absent_rate > 0.3:
                risk += 30
                factors.append(f"High absenteeism ({absent_rate:.0%})")
            elif absent_rate > 0.15:
                risk += 15
                factors.append(f"Moderate absenteeism ({absent_rate:.0%})")
        else:
            risk += 5
            factors.append("No attendance data")

        # --- Mood Risk ---
        emp_mood = mood_df[mood_df["emp_id"] == eid] if not mood_df.empty else pd.DataFrame()
        if not emp_mood.empty:
            if "remarks" in emp_mood.columns:
                stressed_count = emp_mood["remarks"].str.contains("Stressed", na=False).sum()
                total_mood = len(emp_mood)
                stress_rate = stressed_count / total_mood if total_mood > 0 else 0
                if stress_rate > 0.5:
                    risk += 30
                    factors.append(f"Frequently stressed ({stress_rate:.0%} logs)")
                elif stress_rate > 0.25:
                    risk += 15
                    factors.append(f"Occasional stress ({stress_rate:.0%} logs)")
            avg_score = pd.to_numeric(emp_mood["mood_score"], errors="coerce").mean()
            if pd.notna(avg_score) and avg_score < 10:
                risk += 10
                factors.append(f"Low avg mood score ({avg_score:.1f}/25)")
        else:
            risk += 5
            factors.append("No mood data available")

        # --- Feedback Risk ---
        emp_fb = feedback_df[feedback_df["receiver_id"] == eid] if not feedback_df.empty else pd.DataFrame()
        if not emp_fb.empty:
            avg_rating = pd.to_numeric(emp_fb["rating"], errors="coerce").mean()
            if pd.notna(avg_rating):
                if avg_rating < 2.5:
                    risk += 20
                    factors.append(f"Poor feedback rating ({avg_rating:.1f}/5)")
                elif avg_rating < 3.5:
                    risk += 10
                    factors.append(f"Below-average feedback ({avg_rating:.1f}/5)")

        # --- Task overdue risk ---
        emp_tasks = tasks_df[tasks_df["emp_id"] == eid] if not tasks_df.empty else pd.DataFrame()
        if not emp_tasks.empty:
            try:
                emp_tasks = emp_tasks.copy()
                emp_tasks["due_date"] = pd.to_datetime(emp_tasks["due_date"], errors="coerce")
                overdue = emp_tasks[
                    (emp_tasks["status"] != "Completed") &
                    (emp_tasks["due_date"] < pd.Timestamp(date.today()))
                ]
                if len(overdue) >= 3:
                    risk += 10
                    factors.append(f"{len(overdue)} overdue tasks")
            except Exception:
                pass

        # Cap at 95 for non-resigned
        risk = min(risk, 95)

        if risk >= 70:
            level = "🔴 High Risk"
        elif risk >= 40:
            level = "🟡 Medium Risk"
        else:
            level = "🟢 Low Risk"

        results.append({
            "Emp_ID": eid,
            "Name": emp["Name"],
            "Department": emp["Department"],
            "Role": emp["Role"],
            "Status": emp["Status"],
            "Risk_Score": risk,
            "Risk_Level": level,
            "Key_Factors": "; ".join(factors) if factors else "No significant risk factors"
        })

    return pd.DataFrame(results).sort_values("Risk_Score", ascending=False)

# -------------------------
# Compute Risk
# -------------------------
with st.spinner("Computing attrition risk scores..."):
    risk_df = compute_attrition_risk(emp_df, att_df, mood_df, feedback_df, tasks_df)

# -------------------------
# Top Metrics
# -------------------------
st.header("📊 Workforce Attrition Overview")

resigned = len(emp_df[emp_df["Status"] == "Resigned"])
total_active = len(emp_df[emp_df["Status"] == "Active"])
attrition_rate = round(resigned / len(emp_df) * 100, 1) if len(emp_df) > 0 else 0

high_risk = len(risk_df[risk_df["Risk_Level"] == "🔴 High Risk"])
medium_risk = len(risk_df[risk_df["Risk_Level"] == "🟡 Medium Risk"])
low_risk = len(risk_df[risk_df["Risk_Level"] == "🟢 Low Risk"])

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Employees", len(emp_df))
col2.metric("Attrition Rate", f"{attrition_rate}%")
col3.metric("🔴 High Risk", high_risk)
col4.metric("🟡 Medium Risk", medium_risk)
col5.metric("🟢 Low Risk", low_risk)

st.divider()

# -------------------------
# Attrition Risk Table
# -------------------------
st.header("🚦 Employee Attrition Risk Scores")

# Filters
col_f1, col_f2, col_f3 = st.columns(3)
filter_risk = col_f1.selectbox("Filter by Risk", ["All", "🔴 High Risk", "🟡 Medium Risk", "🟢 Low Risk", "🔴 Resigned"])
filter_dept = col_f2.selectbox("Filter by Department", ["All"] + sorted(emp_df["Department"].dropna().unique()))
filter_status = col_f3.selectbox("Status", ["All", "Active", "Resigned"])

display_risk = risk_df.copy()
if filter_risk != "All":
    display_risk = display_risk[display_risk["Risk_Level"] == filter_risk]
if filter_dept != "All":
    display_risk = display_risk[display_risk["Department"] == filter_dept]
if filter_status != "All":
    display_risk = display_risk[display_risk["Status"] == filter_status]

st.dataframe(display_risk, use_container_width=True, height=350)

st.divider()

# -------------------------
# Attrition Analytics Charts
# -------------------------
st.header("📈 Attrition Analytics")

col_chart1, col_chart2, col_chart3 = st.columns(3)

# Chart 1: Risk distribution
with col_chart1:
    st.subheader("Risk Level Distribution")
    risk_counts = risk_df["Risk_Level"].value_counts()
    fig1, ax1 = plt.subplots(figsize=(5, 4))
    colors_map = {"🔴 High Risk": "#e74c3c", "🟡 Medium Risk": "#f39c12", "🟢 Low Risk": "#2ecc71", "🔴 Resigned": "#95a5a6"}
    bar_colors = [colors_map.get(r, "#3498db") for r in risk_counts.index]
    bars = ax1.bar(risk_counts.index, risk_counts.values, color=bar_colors)
    ax1.set_ylabel("Count")
    for bar in bars:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
    plt.xticks(rotation=15, ha="right", fontsize=8)
    plt.tight_layout()
    st.pyplot(fig1)
    plt.close(fig1)

# Chart 2: Attrition by department
with col_chart2:
    st.subheader("Resigned by Department")
    resigned_df = emp_df[emp_df["Status"] == "Resigned"]
    if not resigned_df.empty:
        dept_resign = resigned_df["Department"].value_counts()
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        ax2.bar(dept_resign.index, dept_resign.values, color="#e74c3c")
        ax2.set_ylabel("Resigned")
        for bar in ax2.patches:
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
        plt.xticks(rotation=15, ha="right", fontsize=8)
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)
    else:
        st.info("No resigned employees.")

# Chart 3: High risk by department
with col_chart3:
    st.subheader("High Risk by Department")
    high_risk_df = risk_df[risk_df["Risk_Level"] == "🔴 High Risk"]
    if not high_risk_df.empty:
        hr_dept = high_risk_df["Department"].value_counts()
        fig3, ax3 = plt.subplots(figsize=(5, 4))
        ax3.bar(hr_dept.index, hr_dept.values, color="#f39c12")
        ax3.set_ylabel("High Risk Count")
        for bar in ax3.patches:
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(int(bar.get_height())), ha="center", va="bottom", fontsize=9)
        plt.xticks(rotation=15, ha="right", fontsize=8)
        plt.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)
    else:
        st.info("No high risk employees found.")

st.divider()

# -------------------------
# AI GENERATED REPORT SECTION
# -------------------------
st.header("🤖 AI-Generated Attrition Report")

def build_attrition_prompt(emp_df, att_df, mood_df, feedback_df, risk_df) -> str:
    """Build a rich data prompt for Claude to analyze."""
    prompt_lines = []
    prompt_lines.append("You are an expert HR analytics AI. Analyze the following workforce data and generate a comprehensive attrition report.\n")

    # Overall stats
    total = len(emp_df)
    active = len(emp_df[emp_df["Status"] == "Active"])
    resigned = len(emp_df[emp_df["Status"] == "Resigned"])
    attrition_pct = round(resigned/total*100, 1) if total > 0 else 0

    prompt_lines.append(f"WORKFORCE OVERVIEW:")
    prompt_lines.append(f"- Total Employees: {total}")
    prompt_lines.append(f"- Active: {active}, Resigned: {resigned}")
    prompt_lines.append(f"- Attrition Rate: {attrition_pct}%\n")

    # Department breakdown
    if "Department" in emp_df.columns:
        dept_stats = emp_df.groupby("Department")["Status"].value_counts().unstack(fill_value=0)
        prompt_lines.append(f"DEPARTMENT BREAKDOWN:\n{dept_stats.to_string()}\n")

    # Top high risk employees
    high_risk = risk_df[risk_df["Risk_Level"] == "🔴 High Risk"].head(10)
    if not high_risk.empty:
        prompt_lines.append(f"TOP HIGH-RISK EMPLOYEES:")
        for _, row in high_risk.iterrows():
            prompt_lines.append(f"  - {row['Name']} ({row['Department']}, {row['Role']}): Score={row['Risk_Score']}, Factors: {row['Key_Factors']}")
        prompt_lines.append("")

    # Mood summary
    if not mood_df.empty and "remarks" in mood_df.columns:
        mood_counts = mood_df["remarks"].str.extract(r"(Happy|Neutral|Stressed)")[0].value_counts().to_dict()
        prompt_lines.append(f"MOOD DATA: {mood_counts}\n")

    # Attendance summary
    if not att_df.empty:
        att_counts = att_df["status"].value_counts().to_dict()
        prompt_lines.append(f"ATTENDANCE: {att_counts}\n")

    # Feedback
    if not feedback_df.empty:
        avg_rating = feedback_df["rating"].mean()
        low_rated = feedback_df[feedback_df["rating"] <= 2]
        prompt_lines.append(f"FEEDBACK: Avg rating={avg_rating:.2f}/5, Low ratings (<= 2): {len(low_rated)}\n")

    prompt_lines.append("""
Please generate a detailed, professional HR attrition report covering:

1. **Executive Summary** — Key attrition metrics and what they mean
2. **Root Cause Analysis** — Why are employees leaving or at risk? (based on mood, attendance, feedback)
3. **Department Risk Assessment** — Which departments need immediate attention?
4. **Employee Profiles at Risk** — Patterns in who is leaving (roles, seniority, departments)
5. **Warning Signs** — What early signals predict resignation?
6. **Retention Recommendations** — 5 specific, actionable strategies to reduce attrition
7. **Priority Actions** — Top 3 things HR should do in the next 30 days

Format the report clearly with numbered sections and bullet points where appropriate.
Be specific, data-driven, and actionable.""")

    return "\n".join(prompt_lines)


def generate_ai_report(prompt: str, api_key: str, model: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": model,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=90
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            return "❌ Invalid API key. Please check your Anthropic API key in the sidebar."
        return f"❌ API Error: {str(e)}"
    except Exception as e:
        return f"❌ Error generating report: {str(e)}"


# -------------------------
# Generate Report Button
# -------------------------
if not api_key:
    st.info("🔑 Enter your Anthropic API key in the sidebar to generate the AI report.")

col_btn1, col_btn2 = st.columns([1, 3])
generate_btn = col_btn1.button("🤖 Generate AI Report", type="primary", use_container_width=True, disabled=not api_key)
regen_btn = col_btn2.button("🔄 Regenerate", use_container_width=False, disabled=not api_key)

if generate_btn or regen_btn:
    with st.spinner("🧠 Claude AI is analyzing your workforce data... This may take 15-30 seconds..."):
        prompt = build_attrition_prompt(emp_df, att_df, mood_df, feedback_df, risk_df)
        ai_report = generate_ai_report(prompt, api_key, ai_model)
        st.session_state["ai_attrition_report"] = ai_report
        st.session_state["ai_report_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

# Display the AI report
if "ai_attrition_report" in st.session_state:
    report_text = st.session_state["ai_attrition_report"]
    report_time = st.session_state.get("ai_report_time", "")

    st.success(f"✅ AI Report generated at {report_time}")

    with st.container():
        st.markdown(
            f"""<div style='background: linear-gradient(135deg, #f8f9fa, #e8f4f8); 
                 border-left: 5px solid #3498db; border-radius: 8px; 
                 padding: 25px; font-size: 14px; line-height: 1.7;'>
            {report_text.replace(chr(10), '<br>')}
            </div>""",
            unsafe_allow_html=True
        )

    st.divider()

    # -------------------------
    # Export Options
    # -------------------------
    st.subheader("📥 Export Report")

    col_exp1, col_exp2 = st.columns(2)

    # Text export
    full_text = f"""WORKFORCE AI ATTRITION REPORT
Generated: {report_time}
By: {username}
{"="*60}

{report_text}

{"="*60}
RISK SCORE TABLE:
{risk_df.to_string(index=False)}
"""
    col_exp1.download_button(
        "📄 Download as TXT",
        full_text,
        file_name=f"ai_attrition_report_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
        use_container_width=True
    )

    # PDF export
    if col_exp2.button("📋 Export as PDF", use_container_width=True):
        # Build a risk chart for PDF
        fig_pdf, ax_pdf = plt.subplots(figsize=(10, 5))
        risk_counts_pdf = risk_df["Risk_Level"].value_counts()
        bar_colors_pdf = [colors_map.get(r, "#3498db") for r in risk_counts_pdf.index]
        ax_pdf.bar(risk_counts_pdf.index, risk_counts_pdf.values, color=bar_colors_pdf)
        ax_pdf.set_title("Employee Attrition Risk Distribution")
        ax_pdf.set_ylabel("Count")
        for bar in ax_pdf.patches:
            ax_pdf.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(int(bar.get_height())), ha="center", va="bottom")
        plt.tight_layout()
        buf_pdf = io.BytesIO()
        fig_pdf.savefig(buf_pdf, format="png", dpi=150, bbox_inches="tight")
        buf_pdf.seek(0)
        chart_png = buf_pdf.read()
        plt.close(fig_pdf)

        pdf_buffer = io.BytesIO()
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=risk_df,
                projects_df=emp_df[emp_df["Status"] == "Resigned"],
                project_fig=chart_png,
                title="AI Workforce Attrition Report"
            )
            pdf_buffer.seek(0)
            st.download_button(
                "📥 Download PDF",
                pdf_buffer,
                f"ai_attrition_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                "application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

else:
    if api_key:
        st.info("👆 Click **Generate AI Report** to get AI-powered insights on your workforce attrition.")

# -------------------------
# Historical Resigned Employees Table
# -------------------------
st.divider()
st.header("📋 Resigned Employees — Full History")

resigned_full = emp_df[emp_df["Status"] == "Resigned"].copy()
if not resigned_full.empty:
    resigned_full = resigned_full.reset_index(drop=True)
    resigned_full.insert(0, "Sr", range(1, len(resigned_full) + 1))

    display_cols = [c for c in ["Sr", "Emp_ID", "Name", "Department", "Role", "Join_Date", "Resign_Date", "Salary", "Location"] if c in resigned_full.columns]
    st.dataframe(resigned_full[display_cols], use_container_width=True)

    # Tenure analysis
    if "Join_Date" in resigned_full.columns and "Resign_Date" in resigned_full.columns:
        st.subheader("📅 Tenure of Resigned Employees")
        resigned_full["Join_Date_dt"] = pd.to_datetime(resigned_full["Join_Date"], errors="coerce")
        resigned_full["Resign_Date_dt"] = pd.to_datetime(resigned_full["Resign_Date"], errors="coerce")
        resigned_full["Tenure_Days"] = (resigned_full["Resign_Date_dt"] - resigned_full["Join_Date_dt"]).dt.days

        valid_tenure = resigned_full[resigned_full["Tenure_Days"] > 0]
        if not valid_tenure.empty:
            avg_tenure = valid_tenure["Tenure_Days"].mean()
            min_tenure = valid_tenure["Tenure_Days"].min()
            max_tenure = valid_tenure["Tenure_Days"].max()

            tc1, tc2, tc3 = st.columns(3)
            tc1.metric("Avg Tenure Before Leaving", f"{int(avg_tenure)} days ({int(avg_tenure/30)} months)")
            tc2.metric("Shortest Tenure", f"{int(min_tenure)} days")
            tc3.metric("Longest Tenure", f"{int(max_tenure)} days")
else:
    st.info("No resigned employees recorded yet.")