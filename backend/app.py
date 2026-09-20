import os
import time
import mimetypes
import base64
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request

from crypto_utils import compute_sha256, encrypt_file, decrypt_file
from database import init_db, get_connection
from blockchain_web3 import (
    create_record,
    grant_access,
    revoke_access,
    check_permission,
    get_record,
    get_block_number,
    explorer_data,
    explorer_blocks,
    get_block_details,
    tx_hash,
    block_number,
)

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)

init_db()

# Add the new metadata columns automatically to older database.db files.
def ensure_upload_metadata_columns():
    conn = get_connection()
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(records)").fetchall()
    }

    new_columns = {
        "document_type": "TEXT NOT NULL DEFAULT 'Other'",
        "uploaded_by_role": "TEXT NOT NULL DEFAULT 'Doctor'",
        "uploaded_by_id": "TEXT NOT NULL DEFAULT ''",
    }

    for name, definition in new_columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE records ADD COLUMN {name} {definition}")

    conn.commit()
    conn.close()


ensure_upload_metadata_columns()

DOCUMENT_TYPES = {
    "Lab Report",
    "Prescription",
    "Doctor Note",
    "Scan / X-Ray",
    "Discharge Summary",
    "Vaccination Record",
    "Medical Certificate",
    "Other",
}

UPLOAD_ROLES = {"Patient", "Doctor"}

ALLOWED_EXTENSIONS = {
    "txt",
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "csv",
    "json",
    "doc",
    "docx",
}


def _record_metadata(record_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT document_type, uploaded_by_role, uploaded_by_id
        FROM records
        WHERE record_id=?
        """,
        (record_id,),
    ).fetchone()
    conn.close()

    if not row:
        return {
            "document_type": "Other",
            "uploaded_by_role": "Unknown",
            "uploaded_by_id": "",
        }

    return {
        "document_type": row[0],
        "uploaded_by_role": row[1],
        "uploaded_by_id": row[2],
    }


def _enrich_explorer_records(records):
    if not records:
        return records

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT record_id, document_type, uploaded_by_role, uploaded_by_id
        FROM records
        """
    ).fetchall()
    conn.close()

    metadata = {
        row[0]: {
            "document_type": row[1],
            "uploaded_by_role": row[2],
            "uploaded_by_id": row[3],
        }
        for row in rows
    }

    for record in records:
        extra = metadata.get(record["record_id"], {})
        record.update({
            "document_type": extra.get("document_type", "Other"),
            "uploaded_by_role": extra.get("uploaded_by_role", "Unknown"),
            "uploaded_by_id": extra.get("uploaded_by_id", ""),
        })

    return records


@app.get("/health")
def health():
    return jsonify({
        "status": "ONLINE",
        "service": "Patient-Centric Decentralized EHR - Solidity",
        "ethereum_block": get_block_number(),
    })


@app.post("/upload-record")
def upload_record():
    filepath = None
    conn = None

    try:
        record_id = request.form.get("record_id", "").strip()
        patient_id = request.form.get("patient_id", "").strip()
        doctor_id = request.form.get("doctor_id", "").strip()
        title = request.form.get("title", "").strip()
        document_type = request.form.get("document_type", "Other").strip()
        uploaded_by_role = request.form.get("uploaded_by_role", "Patient").strip()
        uploaded_by_id = request.form.get("uploaded_by_id", "").strip()
        uploaded_file = request.files.get("file")

        if not all([record_id, patient_id, title, uploaded_file, uploaded_by_id]):
            return jsonify(
                status="ERROR",
                reason="Record ID, patient ID, title, uploader ID, and file are required.",
            ), 400

        if uploaded_by_role not in UPLOAD_ROLES:
            return jsonify(
                status="ERROR",
                reason=f"Uploader role must be one of: {', '.join(sorted(UPLOAD_ROLES))}.",
            ), 400

        if document_type not in DOCUMENT_TYPES:
            return jsonify(
                status="ERROR",
                reason=f"Invalid document type: {document_type}.",
            ), 400

        # A patient-uploaded document is not tied to a doctor at creation time.
        if uploaded_by_role == "Patient":
            if uploaded_by_id != patient_id:
                return jsonify(
                    status="ERROR",
                    reason="For a patient upload, Uploader ID must match Patient ID.",
                ), 400
            doctor_id = "NOT_ASSIGNED"
        else:
            if not doctor_id:
                return jsonify(
                    status="ERROR",
                    reason="Doctor ID is required when the uploader role is Doctor.",
                ), 400
            if uploaded_by_id != doctor_id:
                return jsonify(
                    status="ERROR",
                    reason="For a doctor upload, Uploader ID must match Doctor ID.",
                ), 400

        filename = uploaded_file.filename or "medical_record"
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension and extension not in ALLOWED_EXTENSIONS:
            return jsonify(
                status="ERROR",
                reason=(
                    f"Unsupported file type '.{extension}'. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ),
            ), 400

        conn = get_connection()
        existing = conn.execute(
            "SELECT record_id FROM records WHERE record_id=?",
            (record_id,),
        ).fetchone()

        if existing:
            conn.close()
            conn = None
            return jsonify(
                status="ERROR",
                reason=f"Record ID '{record_id}' already exists.",
            ), 409

        original_bytes = uploaded_file.read()
        if not original_bytes:
            conn.close()
            conn = None
            return jsonify(status="ERROR", reason="Uploaded file is empty."), 400

        mime_type = (
            uploaded_file.mimetype
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        record_hash = compute_sha256(original_bytes)
        ciphertext, key, iv = encrypt_file(original_bytes)

        filepath = STORAGE_DIR / f"{record_id}.enc"
        with open(filepath, "wb") as f:
            f.write(ciphertext)

        conn.execute(
            """
            INSERT INTO records
            (
                record_id,
                patient_id,
                doctor_id,
                title,
                original_filename,
                mime_type,
                encrypted_filepath,
                aes_key,
                iv,
                uploaded_at,
                document_type,
                uploaded_by_role,
                uploaded_by_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                patient_id,
                doctor_id,
                title,
                filename,
                mime_type,
                str(filepath),
                key,
                iv,
                time.time(),
                document_type,
                uploaded_by_role,
                uploaded_by_id,
            ),
        )
        conn.commit()
        conn.close()
        conn = None

        try:
            # Medical bytes and the AES key remain off-chain.
            # Only the existing Solidity record interface is used.
            receipt = create_record(
                record_id,
                patient_id,
                doctor_id,
                title,
                record_hash,
            )
        except Exception:
            cleanup_conn = get_connection()
            cleanup_conn.execute(
                "DELETE FROM records WHERE record_id=?",
                (record_id,),
            )
            cleanup_conn.commit()
            cleanup_conn.close()

            if filepath and filepath.exists():
                filepath.unlink()

            raise

        return jsonify({
            "status": "SUCCESS",
            "record_id": record_id,
            "record_hash": record_hash,
            "document_type": document_type,
            "uploaded_by_role": uploaded_by_role,
            "uploaded_by_id": uploaded_by_id,
            "block": block_number(receipt),
            "transaction_hash": tx_hash(receipt),
        }), 201

    except Exception as e:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

        print("UPLOAD ERROR:", repr(e))
        return jsonify(status="ERROR", reason=str(e)), 500


@app.get("/patient-records/<patient_id>")
def patient_records(patient_id):
    patient_id = patient_id.strip()

    if not patient_id:
        return jsonify(
            status="ERROR",
            reason="Patient ID is required.",
        ), 400

    try:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT
                record_id,
                title,
                document_type,
                original_filename,
                uploaded_by_role,
                uploaded_by_id,
                doctor_id,
                uploaded_at
            FROM records
            WHERE patient_id=?
            ORDER BY uploaded_at DESC
            """,
            (patient_id,),
        ).fetchall()
        conn.close()

        records = [
            {
                "record_id": row[0],
                "title": row[1],
                "document_type": row[2],
                "filename": row[3],
                "uploaded_by_role": row[4],
                "uploaded_by_id": row[5],
                "doctor_id": row[6],
                "uploaded_at": row[7],
            }
            for row in rows
        ]

        return jsonify(
            status="SUCCESS",
            records=records,
        ), 200

    except Exception as e:
        print("PATIENT RECORDS ERROR:", repr(e))
        return jsonify(
            status="ERROR",
            reason=str(e),
        ), 500


@app.post("/grant-access")
def grant():
    try:
        data = request.get_json(force=True)
        patient_id = data["patient_id"]
        doctor_id = data["doctor_id"]
        record_id = data["record_id"]
        duration_hours = float(data.get("duration_hours", 24))

        if duration_hours <= 0:
            return jsonify(
                status="ERROR",
                reason="Duration must be positive.",
            ), 400

        conn = get_connection()
        row = conn.execute(
            """
            SELECT record_id
            FROM records
            WHERE record_id=? AND patient_id=?
            """,
            (record_id, patient_id),
        ).fetchone()
        conn.close()

        if not row:
            return jsonify(
                status="ERROR",
                reason="Record not found for this patient.",
            ), 404

        receipt = grant_access(
            patient_id,
            doctor_id,
            record_id,
            int(duration_hours * 3600),
        )

        allowed, valid_until = check_permission(
            patient_id,
            doctor_id,
            record_id,
        )

        return jsonify({
            "status": "SUCCESS",
            "block": block_number(receipt),
            "transaction_hash": tx_hash(receipt),
            "valid_until": valid_until,
            "allowed": allowed,
        }), 200

    except Exception as e:
        print("GRANT ERROR:", repr(e))
        return jsonify(
            status="ERROR",
            reason=str(e),
        ), 500


@app.post("/revoke-access")
def revoke():
    try:
        data = request.get_json(force=True)
        patient_id = data["patient_id"]
        doctor_id = data["doctor_id"]
        record_id = data["record_id"]

        receipt = revoke_access(
            patient_id,
            doctor_id,
            record_id,
        )

        return jsonify({
            "status": "SUCCESS",
            "block": block_number(receipt),
            "transaction_hash": tx_hash(receipt),
        }), 200

    except Exception as e:
        print("REVOKE ERROR:", repr(e))
        return jsonify(
            status="ERROR",
            reason=str(e),
        ), 500


@app.post("/view-record")
def view_record():
    try:
        data = request.get_json(force=True)

        patient_id = data["patient_id"]
        doctor_id = data["doctor_id"]
        record_id = data["record_id"]

        allowed, valid_until = check_permission(
            patient_id,
            doctor_id,
            record_id,
        )

        if not allowed:
            return jsonify(
                status="FORBIDDEN",
                reason="No valid blockchain authorization (or permission expired/revoked).",
            ), 403

        onchain = get_record(record_id)

        if not onchain[6]:
            return jsonify(
                status="NOT_FOUND",
                reason="Record not found on blockchain.",
            ), 404

        expected_hash = "0x" + bytes(onchain[4]).hex()
        metadata = _record_metadata(record_id)

        conn = get_connection()
        row = conn.execute(
            """
            SELECT
                encrypted_filepath,
                aes_key,
                iv,
                original_filename,
                mime_type
            FROM records
            WHERE record_id=? AND patient_id=?
            """,
            (record_id, patient_id),
        ).fetchone()
        conn.close()

        if not row:
            return jsonify(
                status="NOT_FOUND",
                reason="Off-chain record metadata missing.",
            ), 404

        filepath, key, iv, filename, mime_type = row

        if not os.path.exists(filepath):
            return jsonify(
                status="NOT_FOUND",
                reason="Encrypted medical file missing.",
            ), 404

        with open(filepath, "rb") as f:
            ciphertext = f.read()

        try:
            decrypted = decrypt_file(
                ciphertext,
                bytes(key),
                bytes(iv),
            )
        except Exception as e:
            print("DECRYPTION ERROR:", repr(e))
            return jsonify(
                status="DECRYPTION_FAILED",
                reason="Unable to decrypt the medical record.",
            ), 500

        current_hash = "0x" + compute_sha256(decrypted)

        if current_hash.lower() != expected_hash.lower():
            return jsonify({
                "status": "INTEGRITY_COMPROMISED",
                "alert": "Decrypted file does not match the SHA-256 fingerprint stored in Solidity.",
                "expected_hash": expected_hash,
                "current_hash": current_hash,
            }), 409

        content = ""

        if mime_type.startswith("text/") or filename.lower().endswith(
            (".txt", ".csv", ".json")
        ):
            content = decrypted.decode(
                "utf-8",
                errors="ignore",
            )

        return jsonify({
            "status": "AUTHORIZED",
            "integrity": "VERIFIED",
            "record_hash": expected_hash,
            "filename": filename,
            "mime_type": mime_type,
            "content": content,
            "file_base64": base64.b64encode(
                decrypted
            ).decode("utf-8"),
            "valid_until": valid_until,
            **metadata,
        }), 200

    except Exception as e:
        print("VIEW ERROR:", repr(e))
        return jsonify(
            status="ERROR",
            reason=str(e),
        ), 500


@app.get("/blockchain")
def blockchain():
    try:
        records = explorer_data()
        records = _enrich_explorer_records(records)

        return jsonify({
            "status": "SUCCESS",
            "ethereum_block": get_block_number(),
            "records": records,
        })

    except Exception as e:
        return jsonify(
            status="ERROR",
            reason=str(e),
        ), 500


@app.get("/blocks")
def blocks():
    try:
        return jsonify({
            "status": "SUCCESS",
            "ethereum_block": get_block_number(),
            "blocks": explorer_blocks(),
        })

    except Exception as e:
        return jsonify(
            status="ERROR",
            reason=str(e),
        ), 500


@app.get("/block/<int:block_number>")
def block_details(block_number):
    try:
        return jsonify({
            "status": "SUCCESS",
            "block": get_block_details(block_number),
        })

    except ValueError as e:
        return jsonify(
            status="ERROR",
            reason=str(e),
        ), 400

    except Exception as e:
        return jsonify(
            status="ERROR",
            reason=str(e),
        ), 500


if __name__ == "__main__":
    print("Patient-Centric Decentralized EHR - Solidity backend")
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
    )
