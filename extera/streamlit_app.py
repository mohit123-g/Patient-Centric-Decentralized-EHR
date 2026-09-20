import base64
import time
import requests
import streamlit as st

API_URL = "http://127.0.0.1:5000"

st.set_page_config(page_title="Decentralized EHR - Solidity", page_icon="🏥", layout="wide")
st.title("🏥 Patient-Centric Decentralized EHR System")
st.caption("AES-256 Off-Chain Storage + SHA-256 + Solidity Smart Contract")

try:
    health = requests.get(f"{API_URL}/health", timeout=3)
    if health.ok:
        st.success(f"🟢 Flask + Ethereum Connected | Ethereum Block: {health.json().get('ethereum_block')}")
    else:
        st.error("Flask backend is not healthy.")
except requests.RequestException:
    st.error("🔴 Flask backend is not running. Start backend/app.py first.")


def post(path, **kwargs):
    try:
        return requests.post(f"{API_URL}{path}", timeout=60, **kwargs)
    except requests.RequestException as e:
        st.error(f"Backend connection error: {e}")
        return None


tab_patient, tab_doctor, tab_consult, tab_ledger = st.tabs([
    "👤 Patient Portal", "👨‍⚕️ Doctor Upload", "📋 Doctor Consultation", "🔗 Blockchain Explorer"
])

with tab_patient:
    st.header("Patient Access Governance")
    st.info("Access permissions are written to the Solidity smart contract.")
    patient_id = st.text_input("Patient ID", "PAT-001", key="pat")
    doctor_id = st.text_input("Doctor ID", "DOC-05", key="doc")
    record_id = st.text_input("Record ID", "REC-104", key="rec")
    duration = st.number_input("Access Duration (Hours)", 1, 72, 24)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Grant Access", use_container_width=True):
            r = post("/grant-access", json={"patient_id": patient_id, "doctor_id": doctor_id, "record_id": record_id, "duration_hours": duration})
            if r is not None:
                if r.ok:
                    d = r.json(); st.success(f"Access Granted in Ethereum Block #{d['block']}"); st.code(d["transaction_hash"])
                else: st.error(r.text)
    with c2:
        if st.button("⛔ Revoke Access", use_container_width=True):
            r = post("/revoke-access", json={"patient_id": patient_id, "doctor_id": doctor_id, "record_id": record_id})
            if r is not None:
                if r.ok:
                    d = r.json(); st.warning(f"Access Revoked in Ethereum Block #{d['block']}"); st.code(d["transaction_hash"])
                else: st.error(r.text)

with tab_doctor:
    st.header("Upload New Medical Record")
    st.info("The medical file stays encrypted off-chain. Solidity stores the SHA-256 fingerprint and audit metadata.")
    doctor_id = st.text_input("Doctor ID", "DOC-99", key="updoc")
    patient_id = st.text_input("Patient ID", "PAT-001", key="uppat")
    record_id = st.text_input("New Record ID", "REC-104", key="uprec")
    title = st.text_input("Record Title", "CBC Blood Test Panel", key="uptitle")
    uploaded = st.file_uploader("Select Medical Report", type=["txt", "pdf", "png", "jpg", "jpeg", "csv", "json"])
    if st.button("🔒 Encrypt & Store + Write Hash to Solidity", use_container_width=True):
        if not uploaded:
            st.warning("Attach a file first.")
        else:
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            data = {"record_id": record_id, "patient_id": patient_id, "doctor_id": doctor_id, "title": title}
            r = post("/upload-record", data=data, files=files)
            if r is not None:
                if r.status_code == 201:
                    d = r.json(); st.success("Record processed successfully!")
                    st.metric("Ethereum Block", d["block"])
                    st.write("SHA-256 fingerprint stored in Solidity:")
                    st.code(d["record_hash"])
                    st.write("Transaction:"); st.code(d["transaction_hash"])
                else: st.error(r.text)

with tab_consult:
    st.header("Doctor Record Access & Integrity Portal")
    st.info("1. Solidity authorization → 2. AES-256 decryption → 3. SHA-256 verification")
    c1, c2, c3 = st.columns(3)
    with c1: doctor_id = st.text_input("Consulting Doctor ID", "DOC-05", key="c_doc")
    with c2: patient_id = st.text_input("Patient ID", "PAT-001", key="c_pat")
    with c3: record_id = st.text_input("Record ID", "REC-104", key="c_rec")
    if st.button("🔑 Access & Verify Record", use_container_width=True):
        r = post("/view-record", json={"doctor_id": doctor_id, "patient_id": patient_id, "record_id": record_id})
        if r is not None:
            if r.status_code == 200:
                d = r.json()
                st.success("✅ ACCESS AUTHORIZED BY SOLIDITY SMART CONTRACT")
                a,b,c = st.columns(3)
                a.metric("Authorization", "VALID ✅")
                b.metric("Decryption", "SUCCESS ✅")
                c.metric("Integrity", "VERIFIED ✅")
                st.subheader("SHA-256 Fingerprint")
                st.code(d["record_hash"])
                if d.get("content"):
                    st.subheader("📄 Decrypted Medical Document")
                    st.text_area("Content", d["content"], height=250)
                else:
                    raw = base64.b64decode(d["file_base64"])
                    st.download_button("⬇️ Download Decrypted Record", raw, file_name=d["filename"], mime=d["mime_type"])
            elif r.status_code == 403:
                st.error("⛔ ACCESS DENIED BY SOLIDITY")
                st.warning(r.json().get("reason", r.text))
            elif r.status_code == 409:
                st.error("🚨 SECURITY ALERT — INTEGRITY COMPROMISED")
                d = r.json(); st.write("Expected:"); st.code(d.get("expected_hash")); st.write("Current:"); st.code(d.get("current_hash"))
            elif r.status_code == 500:
                st.error("🔐 DECRYPTION FAILED")
                st.warning(r.json().get("reason", r.text))
            else:
                st.error(f"Error {r.status_code}: {r.text}")

with tab_ledger:
    st.header("🔗 Solidity Blockchain Explorer")
    st.info("This explorer reads records directly from the deployed PatientEHR smart contract through Flask/Web3.")
    if st.button("🔄 Refresh Ledger", use_container_width=True):
        st.rerun()
    try:
        r = requests.get(f"{API_URL}/blockchain", timeout=10)
        if r.ok:
            d = r.json()
            st.metric("Current Ethereum Block", d.get("ethereum_block"))
            records = d.get("records", [])
            st.metric("Records Stored On-Chain", len(records))
            for item in reversed(records):
                with st.expander(f"📦 {item['record_id']} — {item['title']}"):
                    st.write(f"Patient: **{item['patient_id']}**")
                    st.write(f"Doctor: **{item['doctor_id']}**")
                    st.write(f"Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['created_at']))}")
                    st.write("SHA-256 / bytes32:")
                    st.code(item["record_hash"])
        else:
            st.error(r.text)
    except requests.RequestException as e:
        st.error(str(e))

st.markdown("---")
st.caption("Patient-Centric Decentralized EHR | Solidity + Ethereum + Web3.py + Flask + Streamlit + AES-256 + SHA-256")
