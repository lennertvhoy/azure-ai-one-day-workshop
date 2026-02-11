import json
import os
from pathlib import Path

import requests
import streamlit as st


st.set_page_config(page_title="AI Operations Desk", page_icon="🤖", layout="wide")

st.title("🤖 AI Operations Desk")
st.caption("Lab 1 Intake + Lab 2 Policy Copilot (enterprise demo)")

lab1_url = st.sidebar.text_input("Lab 1 API URL", value=os.getenv("LAB1_URL", "https://app-aiws-1831894484.azurewebsites.net"))
lab2_url = st.sidebar.text_input("Lab 2 API URL", value=os.getenv("LAB2_URL", "https://app-aiws-rag-159277257.azurewebsites.net"))
timeout = st.sidebar.slider("Request timeout (s)", min_value=5, max_value=120, value=30)

st.sidebar.markdown("---")
st.sidebar.caption("Tip: use deployed Azure URLs during class")

tab1, tab2, tab3 = st.tabs(["1) Intake", "2) Policy Copilot", "3) Connected Flow"])


with tab1:
    st.subheader("Document Intake (Lab 1)")
    text = st.text_area(
        "Paste raw document text",
        height=240,
        value="Invoice INV-204 from Contoso Office Supplies for EUR 2,430 due in 14 days.",
    )

    if st.button("Run Intake", type="primary"):
        try:
            r = requests.post(f"{lab1_url.rstrip('/')}/intake", json={"text": text}, timeout=timeout)
            st.write(f"Status: {r.status_code}")
            if r.ok:
                st.json(r.json())
            else:
                st.error(r.text)
        except Exception as e:
            st.error(str(e))


with tab2:
    st.subheader("Policy Copilot (Lab 2)")
    q = st.text_input("Ask a policy question", value="When should I report phishing?")
    if st.button("Ask Copilot", type="primary"):
        try:
            r = requests.post(f"{lab2_url.rstrip('/')}/chat", json={"question": q}, timeout=timeout)
            st.write(f"Status: {r.status_code}")
            if r.ok:
                data = r.json()
                st.markdown("### Answer")
                st.write(data.get("answer", ""))
                st.markdown("### Citations")
                st.json(data.get("citations", []))
                with st.expander("Raw response"):
                    st.json(data)
            else:
                st.error(r.text)
        except Exception as e:
            st.error(str(e))


with tab3:
    st.subheader("Connected Flow: Intake -> Generate Search Doc -> Ask Question")
    text2 = st.text_area(
        "Incoming document text",
        height=180,
        value=(
            "Incident report: Employee received a phishing email requesting MFA reset. "
            "Clicked link but did not submit password. Reported to IT after 20 minutes."
        ),
    )
    q2 = st.text_input("Question to ask after intake", value="What should happen after a phishing report?")

    if st.button("Run Connected Demo", type="primary"):
        col_a, col_b = st.columns(2)
        try:
            intake = requests.post(f"{lab1_url.rstrip('/')}/intake", json={"text": text2}, timeout=timeout)
            with col_a:
                st.markdown("#### Lab 1 Intake Result")
                st.write(f"Status: {intake.status_code}")
                if intake.ok:
                    st.json(intake.json())
                else:
                    st.error(intake.text)

            chat = requests.post(f"{lab2_url.rstrip('/')}/chat", json={"question": q2}, timeout=timeout)
            with col_b:
                st.markdown("#### Lab 2 Chat Result")
                st.write(f"Status: {chat.status_code}")
                if chat.ok:
                    st.json(chat.json())
                else:
                    st.error(chat.text)

            st.info(
                "For full ingestion bridge, run scripts/demo/run_pipeline.py to push many docs via Lab1 into Lab2 index."
            )
        except Exception as e:
            st.error(str(e))

st.markdown("---")
st.caption("Made for Azure AI One-Day Workshop")
