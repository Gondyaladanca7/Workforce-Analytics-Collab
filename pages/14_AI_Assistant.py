# pages/14_AI_Assistant.py
"""
AI Workforce Assistant — Workforce Intelligence System
- Powered by Claude AI (Anthropic)
- Knows all your workforce data: employees, attendance, mood, tasks, projects, feedback
- Ask anything about your team in plain English
- Role-based data access
- Full conversation history
"""

import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db

# -------------------------
# Page Config & Auth
# -------------------------
st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "Unknown")

st.title("🤖 AI Workforce Assistant")
st.caption("Ask anything about your workforce — powered by Claude AI")

# -------------------------
# API Key Setup (Sidebar)
# -------------------------
st.sidebar.header("🔑 AI Configuration")
api_key = st.sidebar.text_input(
    "Anthropic API Key",
    type="password",
    placeholder="sk-ant-...",
    help="Get your key at console.anthropic.com"
)

ai_model = st.sidebar.selectbox(
    "Model",
    ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    index=0
)

max_tokens = st.sidebar.slider("Max Response Length", 200, 2000, 800)

if not api_key:
    st.info(
        "🔑 **To activate AI:** Enter your Anthropic API key in the sidebar.\n\n"
        "Get one free at [console.anthropic.com](https://console.anthropic.com). "
        "Your key is never stored — it only lives in your browser session."
    )

# -------------------------
# Load All Workforce Data
# -------------------------
@st.cache_data(ttl=60)
def load_all_data():
    try:
        employees = db.fetch_employees()
        attendance = db.fetch_attendance()
        mood = db.fetch_mood_logs()
        tasks = db.fetch_tasks()
        feedback = db.fetch_feedback()
        projects = db.fetch_projects()
        return employees, attendance, mood, tasks, feedback, projects
    except Exception as e:
        return (pd.DataFrame(),) * 6

employees_df, attendance_df, mood_df, tasks_df, feedback_df, projects_df = load_all_data()

# -------------------------
# Build Data Context for AI
# -------------------------
def build_workforce_context(role: str) -> str:
    lines = []
    lines.append(f"=== WORKFORCE INTELLIGENCE SYSTEM — DATA SNAPSHOT ===")
    lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Accessed by: {username} (Role: {role})\n")

    # Employees
    if not employees_df.empty:
        total = len(employees_df)
        active = len(employees_df[employees_df["Status"] == "Active"])
        resigned = len(employees_df[employees_df["Status"] == "Resigned"])
        depts = employees_df["Department"].value_counts().to_dict()
        lines.append(f"EMPLOYEES: Total={total}, Active={active}, Resigned={resigned}")
        lines.append(f"  By Department: {depts}")

        if role in ["Admin", "HR", "Manager"]:
            sample = employees_df[["Emp_ID", "Name", "Department", "Role", "Status", "Salary", "Join_Date"]].head(30)
            lines.append(f"  Sample records:\n{sample.to_string(index=False)}")

    # Attendance
    if not attendance_df.empty:
        att_counts = attendance_df["status"].value_counts().to_dict()
        lines.append(f"\nATTENDANCE: {att_counts}")
        if role in ["Admin", "HR", "Manager"]:
            recent_att = attendance_df.tail(20)[["emp_id", "date", "status"]]
            lines.append(f"  Recent:\n{recent_att.to_string(index=False)}")

    # Mood
    if not mood_df.empty:
        lines.append(f"\nMOOD LOGS: {len(mood_df)} entries")
        if "remarks" in mood_df.columns:
            mood_summary = mood_df["remarks"].str.extract(r"(Happy|Neutral|Stressed)")[0].value_counts().to_dict()
            lines.append(f"  Mood breakdown: {mood_summary}")
        if role in ["Admin", "HR", "Manager"]:
            recent_mood = mood_df.tail(20)[["emp_id", "mood_score", "remarks", "log_date"]]
            lines.append(f"  Recent:\n{recent_mood.to_string(index=False)}")

    # Tasks
    if not tasks_df.empty:
        task_status = tasks_df["status"].value_counts().to_dict()
        task_priority = tasks_df["priority"].value_counts().to_dict()
        lines.append(f"\nTASKS: Status={task_status}, Priority={task_priority}")

    # Feedback
    if not feedback_df.empty:
        avg_rating = feedback_df["rating"].mean()
        lines.append(f"\nFEEDBACK: {len(feedback_df)} entries, Avg Rating={avg_rating:.2f}/5")

    # Projects
    if not projects_df.empty:
        proj_status = projects_df["status"].value_counts().to_dict()
        avg_progress = projects_df["progress"].mean()
        lines.append(f"\nPROJECTS: {proj_status}, Avg Progress={avg_progress:.1f}%")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a smart, professional AI HR & Workforce Analytics Assistant embedded inside a Workforce Intelligence System. 

Your job is to help HR managers, admins, and team leads understand their workforce data, identify trends, answer HR questions, and provide actionable recommendations.

You have access to real-time data from the system including:
- Employee records (headcount, departments, roles, salaries, status)
- Attendance logs
- Mood/wellbeing survey data
- Tasks and deadlines
- Employee feedback and ratings
- Project health and progress

Guidelines:
- Be concise, professional, and data-driven
- Always reference specific numbers from the data when available
- Provide actionable insights and recommendations
- Flag potential HR risks (high attrition, poor mood, attendance issues)
- Respect confidentiality — don't expose sensitive salary data to non-admin users
- Format responses clearly with headings where helpful
- If asked something outside workforce data, politely redirect"""


def ask_claude(messages: list, context: str, api_key: str) -> str:
    """Call Claude API with workforce context injected."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    system_with_data = SYSTEM_PROMPT + "\n\n" + context

    payload = {
        "model": ai_model,
        "max_tokens": max_tokens,
        "system": system_with_data,
        "messages": messages
    }

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            return "❌ Invalid API key. Please check your Anthropic API key in the sidebar."
        elif response.status_code == 429:
            return "⚠️ Rate limit reached. Please wait a moment and try again."
        else:
            return f"❌ API Error {response.status_code}: {str(e)}"
    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. Please try again."
    except Exception as e:
        return f"❌ Error: {str(e)}"


# -------------------------
# Quick Action Buttons
# -------------------------
st.subheader("⚡ Quick Insights")

quick_prompts = [
    "📊 Give me a full workforce summary",
    "⚠️ Who has poor attendance this month?",
    "😟 Which employees seem stressed or unhappy?",
    "🔴 Which projects are at risk?",
    "📋 What tasks are overdue or high priority?",
    "💰 Compare salaries across departments",
    "📉 Is there a resignation pattern I should know about?",
    "🌟 Who are the highest-rated employees based on feedback?",
]

cols = st.columns(4)
quick_selected = None
for i, prompt in enumerate(quick_prompts):
    if cols[i % 4].button(prompt, use_container_width=True, key=f"quick_{i}"):
        quick_selected = prompt

st.divider()

# -------------------------
# Chat Interface
# -------------------------
if "ai_messages" not in st.session_state:
    st.session_state["ai_messages"] = []

# Display chat history
chat_container = st.container()
with chat_container:
    for msg in st.session_state["ai_messages"]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg["content"])

# Chat input
user_input = st.chat_input("Ask anything about your workforce... (e.g. 'Which department has highest turnover?')")

# Handle quick button or typed input
prompt_to_use = None
if quick_selected:
    prompt_to_use = quick_selected.split(" ", 1)[1]  # strip emoji prefix
elif user_input:
    prompt_to_use = user_input

if prompt_to_use:
    if not api_key:
        st.error("🔑 Please enter your Anthropic API key in the sidebar to use the AI assistant.")
    else:
        # Add user message
        st.session_state["ai_messages"].append({"role": "user", "content": prompt_to_use})

        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt_to_use)

        # Build context and call AI
        context = build_workforce_context(role)

        with chat_container:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Analyzing your workforce data..."):
                    # Keep last 10 messages for context window
                    recent_messages = st.session_state["ai_messages"][-10:]
                    response = ask_claude(recent_messages, context, api_key)
                    st.markdown(response)

        st.session_state["ai_messages"].append({"role": "assistant", "content": response})
        st.rerun()


# -------------------------
# Sidebar: Chat Controls
# -------------------------
st.sidebar.divider()
st.sidebar.subheader("💬 Chat Controls")

if st.sidebar.button("🗑️ Clear Conversation"):
    st.session_state["ai_messages"] = []
    st.rerun()

msg_count = len(st.session_state.get("ai_messages", []))
st.sidebar.metric("Messages in Session", msg_count)

st.sidebar.divider()
st.sidebar.subheader("📊 Data Loaded")
st.sidebar.write(f"👥 Employees: {len(employees_df)}")
st.sidebar.write(f"📋 Attendance: {len(attendance_df)}")
st.sidebar.write(f"😊 Mood Logs: {len(mood_df)}")
st.sidebar.write(f"✅ Tasks: {len(tasks_df)}")
st.sidebar.write(f"💬 Feedback: {len(feedback_df)}")
st.sidebar.write(f"📈 Projects: {len(projects_df)}")

# -------------------------
# Export Conversation
# -------------------------
if st.session_state.get("ai_messages"):
    st.divider()
    st.subheader("💾 Export Conversation")

    chat_export = "\n\n".join(
        f"{'USER' if m['role'] == 'user' else 'AI ASSISTANT'}: {m['content']}"
        for m in st.session_state["ai_messages"]
    )
    full_export = f"AI Workforce Assistant — Conversation Export\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\nUser: {username}\n\n{'='*60}\n\n{chat_export}"

    st.download_button(
        "📥 Download Conversation as TXT",
        full_export,
        file_name=f"ai_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain"
    )