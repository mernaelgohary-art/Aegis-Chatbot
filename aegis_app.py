import streamlit as st
import ollama
import time
import re
import pandas as pd
import email
import hashlib
import uuid
import json
import os
import numpy as np  # Required for statistical calculations
from datetime import datetime
from fpdf import FPDF
# Make sure your db_manager.py is in the same folder
from db_manager import save_chat_message, get_all_sessions, get_session_history, search_sessions

# --- CONFIGURATION ---
st.set_page_config(page_title="AEGIS SOC Dashboard", page_icon="🛡️", layout="wide")

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "threat_summary" not in st.session_state: st.session_state.threat_summary = None
if "analysis_results" not in st.session_state: st.session_state.analysis_results = None

# --- STIX HELPERS ---
def generate_stix_indicator(name, pattern, description):
    return {
        "type": "indicator", "spec_version": "2.1", "id": f"indicator--{uuid.uuid4()}",
        "name": name, "pattern": f"[{pattern}]", "pattern_type": "stix",
        "description": description, "created": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "modified": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    }

def generate_stix_bundle(objects):
    return {"type": "bundle", "id": f"bundle--{uuid.uuid4()}", "objects": objects}

# --- PERSISTENCE LAYER ---
def save_to_intel_library(stix_object, filename="intel_library.json"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try: data = json.load(f)
            except json.JSONDecodeError: data = {"type": "bundle", "objects": []}
    else:
        data = {"type": "bundle", "objects": []}

    existing_ids = {obj.get("id") for obj in data.get("objects", [])}
    new_objects = stix_object.get("objects", [])
    for obj in new_objects:
        if obj.get("id") not in existing_ids:
            data["objects"].append(obj)
            existing_ids.add(obj.get("id"))
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# --- LOG PARSER (Updated with Z-Score Visibility) ---
def analyze_logs(log_text):
    patterns = {
        "Brute Force Attempt": {"regex": r"(?i)(failed password|invalid user|authentication failure|login failed)", "mitre": "T1110", "risk": 85},
        "SQL Injection": {"regex": r"(?i)(union.*select|drop table|select.*from|--|' OR '1'='1)", "mitre": "T1190", "risk": 95},
        "Unauthorized Access": {"regex": r"(?i)(permission denied|access denied|not authorized)", "mitre": "T1078", "risk": 70},
        "Port Scan/Network": {"regex": r"(?i)(connection reset|refused|syn flood|port scan)", "mitre": "T1046", "risk": 60}
    }
    stats = {k: len(re.findall(v["regex"], log_text)) for k, v in patterns.items()}
    counts = np.array(list(stats.values()))
    
    # Calculate Z-Scores for all patterns
    z_scores = {}
    mean = np.mean(counts)
    std = np.std(counts)
    
    for k, count in stats.items():
        if std > 0:
            z_scores[k] = round((count - mean) / std, 2)
        else:
            z_scores[k] = 0.0

    # Determine Anomalies (Z-Score > 1.5 triggers alert)
    threshold_z = 1.5
    anomalies = [f"🚨 ALERT: Statistical Anomaly in {k} (Z-Score: {z_scores[k]})" for k, score in z_scores.items() if score > threshold_z]
    
    summary = None
    for k, score in z_scores.items():
        if score > threshold_z:
            summary = {"type": k, "score": patterns[k]["risk"], "mitre": patterns[k]["mitre"]}
            break
            
    stix_list = [generate_stix_indicator(k, f"log:event_type = '{k}'", f"Anomaly detected") for k in stats if z_scores[k] > threshold_z]
    stix_output = generate_stix_bundle(stix_list) if stix_list else {}
    
    return stats, z_scores, anomalies, stix_output, summary

# --- PDF GENERATOR ---
def create_pdf(messages, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"Security Report: {title}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for msg in messages:
        role = msg['role'].capitalize()
        content = str(msg['content']).encode('latin-1', 'replace').decode('latin-1')
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=f"{role}:", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 10, txt=content)
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
with st.sidebar:
    st.header("AEGIS Dashboard v1.0")
    st.info("AEGIS is a SOC assistant for automated log analysis and incident response.")
    
    st.header("Chat History")
    if st.button("➕ Start New Chat"):
        st.session_state.messages = []
        st.session_state.threat_summary = None
        st.session_state.current_session_id = "new"
        st.rerun()

    st.subheader("Model Knowledge Base")
    selected_info_model = st.selectbox("Learn about models:", ["soc-bot:latest", "mistral:latest", "qwen2.5-coder:7b", "llama3:latest"])
    
    search_term = st.text_input("🔍 Search History...")
    raw_sessions = search_sessions(search_term) if search_term else get_all_sessions()
    session_map = {f"{title} | {model}": sid for sid, title, model in raw_sessions}
    selected_display = st.selectbox("Your Saved Chats", ["Select a chat..."] + list(session_map.keys()))

    if selected_display != "Select a chat..." and selected_display != st.session_state.get("last_selected"):
        sid = session_map[selected_display]
        st.session_state.messages = get_session_history(sid)
        st.session_state.current_session_id = sid
        st.session_state.last_selected = selected_display
        st.rerun()

    if st.session_state.get("messages"): 
        pdf_data = create_pdf(st.session_state.messages, "AEGIS_Security_Report")
        st.download_button("📄 Print to PDF", pdf_data, "SOC_Report.pdf", "application/pdf")

    selected_models = st.multiselect("Select Models to Compare", ["soc-bot:latest", "mistral:latest", "qwen2.5-coder:7b", "llama3:latest"], default=["soc-bot:latest"])

# --- MAIN DASHBOARD ---
st.title("🛡️ AEGIS SOC Dashboard")

if st.session_state.threat_summary:
    data = st.session_state.threat_summary
    with st.container(border=True):
        st.subheader("⚠️ Active Threat Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Attack Type", data['type'])
        c2.metric("Risk Score", f"{data['score']}/100")
        c3.metric("Status", "DETECTED")
        c4.metric("MITRE ID", data['mitre'])

tab1, tab2, tab3 = st.tabs(["💬 Incident Response & SOAR", "📊 Log Intelligence", "📧 Forensics Analysis"])

with tab1:
    st.subheader("SOAR Playbook Generator")
    playbook_choice = st.selectbox("Select Playbook Scenario:", ["Ransomware Response", "Phishing Investigation", "SQL Injection Containment"])
    if st.button("🚀 Trigger Playbook"):
        playbook_prompt = f"Create a step-by-step SOAR playbook for {playbook_choice}. Include containment, eradication, and recovery steps."
        st.session_state.messages.append({"role": "user", "content": playbook_prompt})
        st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.markdown(message["content"])

    if prompt := st.chat_input("Ask AEGIS..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        soar_system_prompt = "You are an expert SOAR Engineer. Identify Attack Classification, Severity Score, Objective, Actions, and SIEM Integration."
        full_responses_summary = ""
        
        for model in selected_models:
            try:
                messages_to_send = [{"role": "system", "content": soar_system_prompt}] + st.session_state.messages
                response = ollama.chat(model=model, messages=messages_to_send)
                content = response['message']['content']
                st.markdown(f"**{model} Response:**\n{content}")
                full_responses_summary += f"### {model}\n{content}\n\n"
            except Exception as e:
                st.error(f"Error with {model}: {e}")

        st.session_state.messages.append({"role": "assistant", "content": full_responses_summary})
        save_chat_message(st.session_state.current_session_id, {"role": "assistant", "content": full_responses_summary}, title=prompt[:20], model_name=", ".join(selected_models))

with tab2:
    st.subheader("📊 Log Intelligence")
    st.info("Paste your logs and click 'Analyze' to view threat intelligence.")
    log_input = st.text_area("Paste logs here:", height=150)
    
    if st.button("Analyze Logs"):
        stats, z_scores, anomalies, stix_data, summary = analyze_logs(log_input)
        st.session_state.analysis_results = (stats, z_scores, anomalies, stix_data, summary, log_input)
        st.session_state.threat_summary = summary
        st.rerun()

    if st.session_state.analysis_results:
        stats, z_scores, anomalies, stix_data, summary, raw_log = st.session_state.analysis_results
        
        # Display Combined Table
        df_display = pd.DataFrame({"Count": stats, "Z-Score": z_scores})
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.caption("Visual Frequency")
            st.bar_chart(df_display["Count"])
        with col2:
            st.caption("Statistical Analysis Table")
            st.dataframe(df_display, use_container_width=True)
            
        for alert in anomalies: st.error(alert)
        
        if stix_data:
            with st.expander("🛡️ Generated STIX Indicators"):
                st.json(stix_data)
                if st.button("💾 Save to Library"):
                    save_to_intel_library(stix_data)
                    st.success("✅ Saved!")

with tab3:
    st.subheader("Forensic Analysis Tools")
    t1, t2, t3 = st.tabs(["Header Decoder", "URL Scoring", "Attachment Sandbox"])
    with t1:
        raw_headers = st.text_area("Paste email headers:")
        if st.button("Decode"): st.json(email.message_from_string(raw_headers))
    with t2:
        url_input = st.text_input("Enter URL:")
        if st.button("Check"):
            if "malicious" in url_input or "phishing" in url_input: st.error("🚨 MALICIOUS")
            elif "google" in url_input or "microsoft" in url_input: st.success("✅ SAFE")
            else: st.warning("⚠️ UNKNOWN")
    with t3:
        uploaded_file = st.file_uploader("Upload attachment:")
        if uploaded_file:
            sha256 = hashlib.sha256(uploaded_file.read()).hexdigest()
            st.code(f"SHA-256: {sha256}")
            if "EICAR" in uploaded_file.name: st.error("🚨 ALERT: Malicious File")