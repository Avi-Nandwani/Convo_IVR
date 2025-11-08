#!/usr/bin/env python3
"""
dashboard/streamlit_app.py

Run:
  pip install streamlit requests
  streamlit run dashboard/streamlit_app.py

The app expects your POC to run on BASE_URL (default http://localhost:8000).
"""
import os
import streamlit as st
import requests
import time

BASE = os.environ.get("BASE_URL", "http://localhost:8000")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", None)

st.set_page_config(page_title="IVR POC Dashboard", layout="wide")

st.title("Conversational IVR — POC Dashboard")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Active Sessions")
    if st.button("Refresh sessions"):
        pass

    try:
        r = requests.get(f"{BASE}/api/sessions")
        sessions = r.json().get("sessions", [])
    except Exception as e:
        st.error(f"Failed to fetch sessions from {BASE}/api/sessions — {e}")
        sessions = []

    if not sessions:
        st.info("No sessions found. Trigger a demo call with `demo/simulate_call.py`.")
    for s in sessions:
        with st.expander(f"Call: {s.get('call_id')}  — status: {s.get('status')}"):
            st.write("From:", s.get("from"))
            st.write("To:", s.get("to"))
            st.write("Last intent:", s.get("last_intent"))
            st.write("Last reply:", s.get("last_reply"))
            st.write("Media out:", s.get("media_out"))
            st.write("Created:", s.get("created_at"))
            st.write("Last update:", s.get("last_update"))

            transcripts = s.get("transcripts") or []
            if transcripts:
                st.subheader("Transcripts (session-store):")
                for t in transcripts:
                    st.write(f"- [{t.get('timestamp')}] {t.get('source')}: {t.get('text')}")
            else:
                st.write("No transcripts in session object.")

            # Buttons
            cols = st.columns(3)
            if cols[0].button(f"Refresh transcripts for {s.get('call_id')}"):
                st.experimental_rerun()

            if cols[1].button(f"Escalate {s.get('call_id')}"):
                try:
                    resp = requests.post(f"{BASE}/api/escalate/{s.get('call_id')}", headers={"X-Webhook-Secret": WEBHOOK_SECRET} if WEBHOOK_SECRET else {})
                    st.write("Escalate response:", resp.text)
                except Exception as e:
                    st.error(f"Failed to escalate: {e}")

            if cols[2].button(f"Open agent UI for {s.get('call_id')}"):
                agent_url = f"{BASE}/agent?call_id={s.get('call_id')}"
                st.write("Agent URL (open in browser):", agent_url)

with col2:
    st.header("Recent Transcripts")
    try:
        r = requests.get(f"{BASE}/api/transcripts?limit=50")
        transcripts_data = r.json().get("transcripts", [])
    except Exception as e:
        st.error(f"Failed to fetch transcripts: {e}")
        transcripts_data = []

    if transcripts_data:
        for t in transcripts_data:
            st.write(f"**{t.get('call_id')}** — [{t.get('timestamp')}] {t.get('source')}")
            st.write(t.get('text'))
            st.write("---")
    else:
        st.info("No transcripts found. Run demo to generate transcripts.")
