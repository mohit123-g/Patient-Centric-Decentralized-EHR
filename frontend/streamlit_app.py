
import base64
import time

import requests
import streamlit as st

API_URL = "http://127.0.0.1:5000"

DOCUMENT_TYPES = [
    "Lab Report",
    "Prescription",
    "Doctor Note",
    "Scan / X-Ray",
    "Discharge Summary",
    "Vaccination Record",
    "Medical Certificate",
    "Other",
]

ALLOWED_TYPES = [
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "txt",
    "csv",
    "json",
    "doc",
    "docx",
]

st.set_page_config(
    page_title="Decentralized EHR | Solidity",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        :root {
            --navy: #07111f;
            --blue: #2563eb;
            --blue2: #60a5fa;
            --green: #10b981;
            --amber: #f59e0b;
            --red: #ef4444;
            --text: #e5eefc;
            --muted: #93a4bd;
            --card: rgba(15, 27, 46, 0.82);
            --border: rgba(148, 163, 184, 0.16);
        }

        .stApp {
            background:
                radial-gradient(circle at 15% 0%, rgba(37,99,235,0.18), transparent 28%),
                radial-gradient(circle at 100% 10%, rgba(16,185,129,0.10), transparent 25%),
                #050b14;
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        .hero {
            padding: 1.45rem 1.6rem;
            border: 1px solid var(--border);
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(13,31,57,.96), rgba(8,20,34,.92));
            box-shadow: 0 18px 50px rgba(0,0,0,.25);
            margin-bottom: 1rem;
        }

        .hero-kicker {
            color: #7dd3fc;
            text-transform: uppercase;
            font-size: .72rem;
            font-weight: 800;
            letter-spacing: .16em;
            margin-bottom: .4rem;
        }

        .hero-title {
            color: white;
            font-size: 2.2rem;
            font-weight: 800;
            margin: 0;
            line-height: 1.1;
        }

        .hero-subtitle {
            color: #a8bbd3;
            margin-top: .55rem;
            font-size: 1rem;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            padding: .45rem .75rem;
            border-radius: 999px;
            border: 1px solid rgba(16,185,129,.28);
            background: rgba(16,185,129,.10);
            color: #86efac;
            font-weight: 700;
            font-size: .82rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #34d399;
            box-shadow: 0 0 12px rgba(52,211,153,.8);
        }

        .flow-strip {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin: .4rem 0 1rem;
        }

        .flow-chip {
            padding: .42rem .7rem;
            border-radius: 999px;
            font-size: .78rem;
            font-weight: 700;
            background: rgba(37,99,235,.12);
            color: #bfdbfe;
            border: 1px solid rgba(96,165,250,.18);
        }

        .block-link {
            padding: .8rem .95rem;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(11, 24, 41, .82);
            margin-bottom: .55rem;
        }

        .muted {
            color: var(--muted);
            font-size: .82rem;
        }

        div[data-testid="stMetric"] {
            background: rgba(12, 25, 43, .78);
            border: 1px solid var(--border);
            padding: .8rem;
            border-radius: 14px;
        }

        div[data-testid="stButton"] button {
            border-radius: 11px;
            font-weight: 700;
            min-height: 2.6rem;
        }

        div[data-testid="stFileUploader"] {
            border-radius: 14px;
        }

        .hash-box {
            padding: .75rem .9rem;
            border-radius: 12px;
            background: #030813;
            border: 1px solid var(--border);
            color: #93c5fd;
            font-family: monospace;
            font-size: .76rem;
            overflow-wrap: anywhere;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path, **kwargs):
    try:
        return requests.get(
            f"{API_URL}{path}",
            timeout=30,
            **kwargs,
        )
    except requests.RequestException as exc:
        st.error(f"Backend connection error: {exc}")
        return None


def api_post(path, **kwargs):
    try:
        return requests.post(
            f"{API_URL}{path}",
            timeout=60,
            **kwargs,
        )
    except requests.RequestException as exc:
        st.error(f"Backend connection error: {exc}")
        return None


def fmt_time(ts):
    if not ts:
        return "—"
    return time.strftime(
        "%d %b %Y • %H:%M:%S",
        time.localtime(ts),
    )


def short_hash(value, left=12, right=10):
    if not value:
        return "—"

    if len(value) <= left + right + 3:
        return value

    return f"{value[:left]}…{value[-right:]}"


def status_badge(ok, label):
    if ok:
        st.markdown(
            f'<div class="status-pill">'
            f'<span class="status-dot"></span>{label}'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.error(label)


health = api_get("/health")
health_data = (
    health.json()
    if health is not None and health.ok
    else {}
)

st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">Secure • Hybrid • Blockchain-backed</div>
        <div class="hero-title">🏥 Patient-Centric Decentralized EHR</div>
        <div class="hero-subtitle">
            Upload reports, prescriptions, scans and clinical documents with AES-256 encryption,
            SHA-256 integrity verification and Solidity-based authorization.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if health is not None and health.ok:
    current_block = health_data.get(
        "ethereum_block",
        0,
    )

    status_badge(
        True,
        f"Flask + Ethereum connected  •  Current block #{current_block}",
    )
else:
    status_badge(
        False,
        "Flask backend is not running. Start backend/app.py first.",
    )


with st.sidebar:
    st.markdown("## 🧭 System Console")
    st.caption("Local Hardhat / Solidity demo network")
    st.markdown("---")
    st.markdown("**Architecture**")
    st.write("🖥️ Streamlit UI")
    st.write("⚙️ Flask API")
    st.write("🔐 AES-256 + SQLite")
    st.write("⛓️ Web3.py + Solidity")
    st.write("🧱 Hardhat Ethereum")
    st.markdown("---")

    if health is not None and health.ok:
        st.success(
            f"Chain online\n\n"
            f"Block #{health_data.get('ethereum_block', 0)}"
        )
    else:
        st.error("Chain/backend offline")

    st.caption(
        "Medical bytes stay encrypted off-chain. "
        "SHA-256 fingerprints and authorization actions are anchored to the blockchain."
    )


tab_patient, tab_upload, tab_consult, tab_ledger = st.tabs(
    [
        "👤 Patient Access",
        "📤 Upload Medical Document",
        "🩺 Consultation & Verify",
        "⛓️ Blockchain Explorer",
    ]
)


# -----------------------------
# Patient Access
# -----------------------------

with tab_patient:
    st.markdown("## Patient Access Governance")
    st.caption(
        "Grant or revoke a doctor's permission through the Solidity smart contract."
    )

    st.markdown(
        '<div class="flow-strip">'
        '<span class="flow-chip">Patient identity</span>'
        '<span class="flow-chip">Doctor identity</span>'
        '<span class="flow-chip">Record</span>'
        '<span class="flow-chip">Time-limited permission</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            patient_id = st.text_input(
                "Patient ID",
                "PAT-001",
                key="pat",
            )

        with c2:
            doctor_id = st.text_input(
                "Doctor ID",
                "DOC-05",
                key="doc",
            )

        with c3:
            record_id = st.text_input(
                "Record ID",
                "REC-104",
                key="rec",
            )

        duration = st.slider(
            "Access duration",
            1,
            72,
            24,
            help="Permission is stored by the Solidity contract.",
        )

        b1, b2 = st.columns(2)

        with b1:
            if st.button(
                "✅ Grant Access",
                use_container_width=True,
                type="primary",
            ):
                r = api_post(
                    "/grant-access",
                    json={
                        "patient_id": patient_id,
                        "doctor_id": doctor_id,
                        "record_id": record_id,
                        "duration_hours": duration,
                    },
                )

                if r is not None:
                    if r.ok:
                        d = r.json()
                        st.success(
                            f"Access granted in block #{d['block']}"
                        )
                        x, y = st.columns(2)
                        x.metric("Block", d["block"])
                        y.metric(
                            "Authorization",
                            "ACTIVE ✅",
                        )
                        st.markdown("**Transaction hash**")
                        st.code(
                            d["transaction_hash"],
                            language="text",
                        )
                    else:
                        try:
                            reason = r.json().get(
                                "reason",
                                r.text,
                            )
                        except Exception:
                            reason = r.text
                        st.error(reason)

        with b2:
            if st.button(
                "⛔ Revoke Access",
                use_container_width=True,
            ):
                r = api_post(
                    "/revoke-access",
                    json={
                        "patient_id": patient_id,
                        "doctor_id": doctor_id,
                        "record_id": record_id,
                    },
                )

                if r is not None:
                    if r.ok:
                        d = r.json()
                        st.warning(
                            f"Access revoked in block #{d['block']}"
                        )
                        st.markdown("**Transaction hash**")
                        st.code(
                            d["transaction_hash"],
                            language="text",
                        )
                    else:
                        try:
                            reason = r.json().get(
                                "reason",
                                r.text,
                            )
                        except Exception:
                            reason = r.text
                        st.error(reason)

    st.markdown("### 📚 My Medical Documents")

    lookup_patient = patient_id.strip()

    if lookup_patient:
        catalog_resp = api_get(
            f"/patient-records/{lookup_patient}"
        )
    else:
        catalog_resp = None

    if catalog_resp is not None and catalog_resp.ok:
        catalog = catalog_resp.json().get(
            "records",
            [],
        )

        if not catalog:
            st.info(
                "No uploaded documents found for this patient yet."
            )
        else:
            for item in catalog:
                label = (
                    f"📄 {item['record_id']} · "
                    f"{item['document_type']} · "
                    f"{item['title']}"
                )

                with st.expander(label):
                    a, b, c = st.columns(3)

                    a.write(
                        f"**Type:** "
                        f"{item['document_type']}"
                    )

                    b.write(
                        f"**Uploaded by:** "
                        f"{item['uploaded_by_role']} / "
                        f"{item['uploaded_by_id']}"
                    )

                    c.write(
                        f"**Date:** "
                        f"{fmt_time(item['uploaded_at'])}"
                    )

                    st.write(
                        f"**Original file:** "
                        f"`{item['filename']}`"
                    )

                    st.write(
                        f"**Doctor on record:** "
                        f"`{item['doctor_id']}`"
                    )
    elif (
        catalog_resp is not None
        and catalog_resp.status_code != 404
    ):
        st.warning(catalog_resp.text)


# -----------------------------
# Upload Medical Document
# -----------------------------

with tab_upload:
    st.markdown("## Upload a Medical Document")

    st.caption(
        "Patients and doctors can upload reports, prescriptions, scans, notes "
        "and other clinical documents. Files are encrypted off-chain; the SHA-256 "
        "fingerprint is registered through Solidity."
    )

    st.markdown(
        '<div class="flow-strip">'
        '<span class="flow-chip">1. Choose uploader</span>'
        '<span class="flow-chip">2. Classify document</span>'
        '<span class="flow-chip">3. SHA-256 fingerprint</span>'
        '<span class="flow-chip">4. AES-256 encryption</span>'
        '<span class="flow-chip">5. SQLite storage</span>'
        '<span class="flow-chip">6. Solidity transaction</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        role = st.radio(
            "Who is uploading this document?",
            [
                "Patient",
                "Doctor",
            ],
            horizontal=True,
            key="upload_role",
        )

        c1, c2 = st.columns(2)

        with c1:
            patient_id = st.text_input(
                "Patient ID",
                "PAT-001",
                key="upload_patient_id",
            )

            uploader_id = st.text_input(
                "Uploader ID",
                (
                    "PAT-001"
                    if role == "Patient"
                    else "DOC-99"
                ),
                key="upload_uploader_id",
                help=(
                    "For a patient upload, this must match the Patient ID. "
                    "For a doctor upload, this must match the Doctor ID."
                ),
            )

            record_id = st.text_input(
                "New Record ID",
                "REC-104",
                key="upload_record_id",
            )

        with c2:
            if role == "Doctor":
                doctor_id = st.text_input(
                    "Doctor ID",
                    "DOC-99",
                    key="upload_doctor_id",
                )
            else:
                doctor_id = "NOT_ASSIGNED"
                st.text_input(
                    "Doctor ID",
                    "Assigned later",
                    key="upload_doctor_display",
                    disabled=True,
                )

            document_type = st.selectbox(
                "Document Type",
                DOCUMENT_TYPES,
                key="upload_document_type",
            )

            default_title = (
                "CBC Blood Test Panel"
                if document_type == "Lab Report"
                else (
                    "Medical Prescription"
                    if document_type == "Prescription"
                    else "Medical Document"
                )
            )

            title = st.text_input(
                "Document Title",
                default_title,
                key="upload_title",
            )

        uploaded = st.file_uploader(
            "Select Medical Document",
            type=ALLOWED_TYPES,
            help=(
                "Examples: PDF report, prescription image, X-ray image, "
                "DOCX note, CSV/JSON lab data."
            ),
            key="medical_upload",
        )

        if uploaded:
            st.caption(
                f"Selected: **{uploaded.name}** · "
                f"{uploaded.size / 1024:.1f} KB · "
                f"{uploaded.type or 'unknown MIME'}"
            )

        if st.button(
            "🔒 Encrypt, Store & Register on Blockchain",
            use_container_width=True,
            type="primary",
        ):
            if not uploaded:
                st.warning(
                    "Attach a medical document first."
                )
            elif not uploader_id.strip():
                st.warning("Enter an uploader ID.")
            elif role == "Doctor" and not doctor_id.strip():
                st.warning("Enter the Doctor ID.")
            else:
                files = {
                    "file": (
                        uploaded.name,
                        uploaded.getvalue(),
                        uploaded.type,
                    )
                }

                data = {
                    "record_id": record_id.strip(),
                    "patient_id": patient_id.strip(),
                    "doctor_id": doctor_id.strip(),
                    "title": title.strip(),
                    "document_type": document_type,
                    "uploaded_by_role": role,
                    "uploaded_by_id": uploader_id.strip(),
                }

                with st.spinner(
                    "Encrypting file, saving metadata, "
                    "and registering SHA-256 on-chain..."
                ):
                    r = api_post(
                        "/upload-record",
                        data=data,
                        files=files,
                    )

                if r is not None:
                    if r.status_code == 201:
                        result = r.json()

                        st.success(
                            "Medical document processed "
                            "and registered successfully."
                        )

                        a, b, c, dcol = st.columns(4)

                        a.metric(
                            "Ethereum Block",
                            result["block"],
                        )

                        b.metric(
                            "Document Type",
                            result["document_type"],
                        )

                        c.metric(
                            "Uploader",
                            result["uploaded_by_role"],
                        )

                        dcol.metric(
                            "Integrity",
                            "SHA-256 ✅",
                        )

                        st.markdown("**Record ID**")
                        st.code(
                            result["record_id"],
                            language="text",
                        )

                        st.markdown(
                            "**SHA-256 fingerprint**"
                        )

                        st.markdown(
                            f'<div class="hash-box">'
                            f'{result["record_hash"]}'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                        st.markdown(
                            "**Transaction hash**"
                        )

                        st.code(
                            result["transaction_hash"],
                            language="text",
                        )

                        st.info(
                            "The medical file is encrypted and stored off-chain. "
                            "The blockchain stores the record metadata/fingerprint, "
                            "not the document bytes."
                        )
                    else:
                        try:
                            reason = r.json().get(
                                "reason",
                                r.text,
                            )
                        except Exception:
                            reason = r.text

                        st.error(reason)


# -----------------------------
# Doctor Consultation
# -----------------------------

with tab_consult:
    st.markdown(
        "## Doctor Record Access & Integrity Portal"
    )

    st.caption(
        "Blockchain authorization → AES-256 decryption → SHA-256 verification"
    )

    st.markdown(
        '<div class="flow-strip">'
        '<span class="flow-chip">🔑 Solidity authorization</span>'
        '<span class="flow-chip">🔓 AES-256 decryption</span>'
        '<span class="flow-chip">🧾 SHA-256 comparison</span>'
        '<span class="flow-chip">✅ Verified record</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            doctor_id = st.text_input(
                "Consulting Doctor ID",
                "DOC-05",
                key="c_doc",
            )

        with c2:
            patient_id = st.text_input(
                "Patient ID",
                "PAT-001",
                key="c_pat",
            )

        with c3:
            record_id = st.text_input(
                "Record ID",
                "REC-104",
                key="c_rec",
            )

        if st.button(
            "🔑 Access & Verify Record",
            use_container_width=True,
            type="primary",
        ):
            r = api_post(
                "/view-record",
                json={
                    "doctor_id": doctor_id,
                    "patient_id": patient_id,
                    "record_id": record_id,
                },
            )

            if r is not None:
                if r.status_code == 200:
                    result = r.json()

                    st.success(
                        "ACCESS AUTHORIZED BY SOLIDITY SMART CONTRACT"
                    )

                    a, b, c = st.columns(3)

                    a.metric(
                        "Authorization",
                        "VALID ✅",
                    )

                    b.metric(
                        "Decryption",
                        "SUCCESS ✅",
                    )

                    c.metric(
                        "Integrity",
                        "VERIFIED ✅",
                    )

                    m1, m2, m3 = st.columns(3)

                    m1.write(
                        f"**Document type:** "
                        f"{result.get('document_type', 'Other')}"
                    )

                    m2.write(
                        f"**Uploaded by:** "
                        f"{result.get('uploaded_by_role', 'Unknown')} / "
                        f"{result.get('uploaded_by_id', '—')}"
                    )

                    m3.write(
                        f"**File:** "
                        f"`{result.get('filename', '—')}`"
                    )

                    st.markdown(
                        "**Blockchain SHA-256 fingerprint**"
                    )

                    st.markdown(
                        f'<div class="hash-box">'
                        f'{result["record_hash"]}'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    if result.get("content"):
                        st.markdown(
                            "### 📄 Decrypted Medical Document"
                        )

                        st.text_area(
                            "Content",
                            result["content"],
                            height=280,
                        )
                    else:
                        raw = base64.b64decode(
                            result["file_base64"]
                        )

                        st.download_button(
                            "⬇️ Download Decrypted Record",
                            raw,
                            file_name=result["filename"],
                            mime=result["mime_type"],
                            use_container_width=True,
                        )

                elif r.status_code == 403:
                    st.error(
                        "⛔ ACCESS DENIED BY SOLIDITY"
                    )

                    try:
                        st.warning(
                            r.json().get(
                                "reason",
                                r.text,
                            )
                        )
                    except Exception:
                        st.warning(r.text)

                elif r.status_code == 409:
                    st.error(
                        "🚨 SECURITY ALERT — INTEGRITY COMPROMISED"
                    )

                    result = r.json()
                    x, y = st.columns(2)

                    with x:
                        st.caption("Expected hash")
                        st.code(
                            result.get(
                                "expected_hash",
                                "",
                            ),
                            language="text",
                        )

                    with y:
                        st.caption("Current hash")
                        st.code(
                            result.get(
                                "current_hash",
                                "",
                            ),
                            language="text",
                        )

                elif r.status_code == 500:
                    st.error(
                        "🔐 DECRYPTION FAILED"
                    )

                    try:
                        st.warning(
                            r.json().get(
                                "reason",
                                r.text,
                            )
                        )
                    except Exception:
                        st.warning(r.text)

                else:
                    st.error(
                        f"Error {r.status_code}: {r.text}"
                    )


# -----------------------------
# Blockchain Explorer
# -----------------------------

with tab_ledger:
    st.markdown("## ⛓️ Blockchain Explorer")
    st.caption(
        "Browse every block on the local Hardhat Ethereum chain and inspect its transactions."
    )

    top_left, top_right = st.columns([1, 4])

    with top_left:
        refresh = st.button(
            "🔄 Refresh Chain",
            use_container_width=True,
        )

    with top_right:
        st.info(
            "Click any block on the left to inspect its hash, parent block, "
            "timestamp, gas, and transactions."
        )

    if refresh:
        st.rerun()

    chain_resp = api_get("/blockchain")
    blocks_resp = api_get("/blocks")

    if (
        chain_resp is not None
        and chain_resp.ok
        and blocks_resp is not None
        and blocks_resp.ok
    ):
        chain_data = chain_resp.json()
        blocks_data = blocks_resp.json()

        records = chain_data.get(
            "records",
            [],
        )

        blocks = blocks_data.get(
            "blocks",
            [],
        )

        total_txs = sum(
            b.get("transaction_count", 0)
            for b in blocks
        )

        latest = chain_data.get(
            "ethereum_block",
            0,
        )

        m1, m2, m3, m4 = st.columns(4)

        m1.metric(
            "Latest Block",
            f"#{latest}",
        )

        m2.metric(
            "Blocks",
            len(blocks),
        )

        m3.metric(
            "Transactions",
            total_txs,
        )

        m4.metric(
            "EHR Records",
            len(records),
        )

        st.markdown("### Chain")

        left, right = st.columns(
            [0.95, 1.65]
        )

        default_block = latest

        if "selected_block" not in st.session_state:
            st.session_state.selected_block = default_block

        if (
            st.session_state.selected_block
            > latest
        ):
            st.session_state.selected_block = default_block

        with left:
            st.markdown("#### 🔗 Blocks")

            for item in reversed(blocks):
                number = item["number"]

                label = (
                    f"🔗 Block #{number}  ·  "
                    f"{item['transaction_count']} tx"
                )

                if st.button(
                    label,
                    key=f"block_{number}",
                    use_container_width=True,
                ):
                    st.session_state.selected_block = number
                    st.rerun()

                st.markdown(
                    f'<div class="block-link">'
                    f"<b>{short_hash(item['hash'], 14, 8)}</b><br>"
                    f'<span class="muted">'
                    f"{fmt_time(item['timestamp'])} · "
                    f"{item['transaction_count']} transaction(s)"
                    f"</span></div>",
                    unsafe_allow_html=True,
                )

        with right:
            selected = st.session_state.selected_block

            detail_resp = api_get(
                f"/block/{selected}"
            )

            if (
                detail_resp is not None
                and detail_resp.ok
            ):
                block = detail_resp.json()["block"]

                st.markdown(
                    f"#### 📦 Block #{block['number']}"
                )

                d1, d2, d3 = st.columns(3)

                d1.metric(
                    "Transactions",
                    block["transaction_count"],
                )

                d2.metric(
                    "Gas Used",
                    f"{block['gas_used']:,}",
                )

                d3.metric(
                    "Gas Limit",
                    f"{block['gas_limit']:,}",
                )

                with st.container(border=True):
                    st.caption("Block hash")
                    st.code(
                        block["hash"],
                        language="text",
                    )

                    st.caption("Parent block hash")
                    st.code(
                        block["parent_hash"],
                        language="text",
                    )

                    x, y = st.columns(2)

                    x.write(
                        f"**Timestamp:** "
                        f"{fmt_time(block['timestamp'])}"
                    )

                    x.write(
                        f"**Miner:** "
                        f"`{block.get('miner') or '—'}`"
                    )

                    y.write(
                        f"**Block size:** "
                        f"{block.get('size', 0):,} bytes"
                    )

                    y.write(
                        f"**Nonce:** "
                        f"`{block.get('nonce') or '—'}`"
                    )

                st.markdown(
                    "#### 🧾 Transactions in this block"
                )

                txs = block.get(
                    "transactions",
                    [],
                )

                if not txs:
                    st.info(
                        "This block contains no transactions."
                    )
                else:
                    for idx, tx in enumerate(
                        txs,
                        start=1,
                    ):
                        action = (
                            "Contract deployment"
                            if not tx.get("to")
                            else "Smart-contract transaction"
                        )

                        status = (
                            "SUCCESS ✅"
                            if tx.get("status") == 1
                            else "REVERTED ❌"
                        )

                        with st.expander(
                            f"TX {idx} · {action} · {status}"
                        ):
                            a, b = st.columns(2)

                            with a:
                                st.caption(
                                    "Transaction hash"
                                )

                                st.code(
                                    tx.get("hash", ""),
                                    language="text",
                                )

                                st.write(
                                    f"**From:** "
                                    f"`{tx.get('from') or '—'}`"
                                )

                                st.write(
                                    f"**To:** "
                                    f"`{tx.get('to') or 'Contract creation'}`"
                                )

                            with b:
                                st.write(
                                    f"**Gas used:** "
                                    f"`{tx.get('gas_used', 0):,}`"
                                )

                                st.write(
                                    f"**Gas limit:** "
                                    f"`{tx.get('gas', 0):,}`"
                                )

                                st.write(
                                    f"**Nonce:** "
                                    f"`{tx.get('nonce', 0)}`"
                                )

                                st.write(
                                    f"**Value:** "
                                    f"`{tx.get('value', '0')} wei`"
                                )

                            if tx.get(
                                "contract_address"
                            ):
                                st.write(
                                    f"**Created contract:** "
                                    f"`{tx['contract_address']}`"
                                )

                            with st.expander(
                                "Show raw transaction input"
                            ):
                                st.code(
                                    tx.get(
                                        "input",
                                        "0x",
                                    ),
                                    language="text",
                                )

        st.markdown(
            "### 📚 On-chain EHR records"
        )

        if not records:
            st.info(
                "No EHR records have been written to the smart contract yet."
            )
        else:
            for item in reversed(records):
                with st.expander(
                    f"📄 {item['record_id']} — "
                    f"{item.get('document_type', 'Other')} — "
                    f"{item['title']}"
                ):
                    a, b, c = st.columns(3)

                    a.write(
                        f"**Patient:** "
                        f"{item['patient_id']}"
                    )

                    b.write(
                        f"**Original doctor field:** "
                        f"`{item['doctor_id']}`"
                    )

                    c.write(
                        f"**Created:** "
                        f"{fmt_time(item['created_at'])}"
                    )

                    st.write(
                        f"**Document type:** "
                        f"{item.get('document_type', 'Other')}"
                    )

                    st.write(
                        f"**Uploaded by:** "
                        f"{item.get('uploaded_by_role', 'Unknown')} / "
                        f"{item.get('uploaded_by_id', '—')}"
                    )

                    st.caption(
                        "SHA-256 / bytes32 stored on-chain"
                    )

                    st.markdown(
                        f'<div class="hash-box">'
                        f'{item["record_hash"]}'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    else:
        st.error(
            "Could not load blockchain explorer data. "
            "Check that Flask and Hardhat are running."
        )


st.markdown("---")
st.caption(
    "Patient-Centric Decentralized EHR  • "
    "Solidity + Ethereum + Web3.py + Flask + Streamlit + AES-256 + SHA-256"
)
