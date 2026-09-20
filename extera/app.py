import os
import time
import mimetypes
import base64
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request

from crypto_utils import compute_sha256, encrypt_file, decrypt_file
from database import init_db, get_connection
from extera.blockchain_web3 import (
    create_record,
    grant_access,
    revoke_access,
    check_permission,
    get_record,
    get_block_number,
    explorer_data,
    tx_hash,
    block_number,
)

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)
init_db()


@app.get("/health")
def health():
    return jsonify({
        "status": "ONLINE",
        "service": "Patient-Centric Decentralized EHR - Solidity",
        "ethereum_block": get_block_number(),
    })


@app.post("/upload-record")
def upload_record():
    try:
        record_id = request.form.get("record_id", "").strip()
        patient_id = request.form.get("patient_id", "").strip()
        doctor_id = request.form.get("doctor_id", "").strip()
        title = request.form.get("title", "").strip()
        uploaded_file = request.files.get("file")

        if not all([record_id, patient_id, doctor_id, title, uploaded_file]):
            return jsonify(status="ERROR", reason="Missing required fields."), 400

        conn = get_connection()
        existing = conn.execute(
            "SELECT record_id FROM records WHERE record_id=?", (record_id,)
        ).fetchone()
        conn.close()
        if existing:
            return jsonify(status="ERROR", reason=f"Record ID '{record_id}' already exists."), 409

        original_bytes = uploaded_file.read()
        if not original_bytes:
            return jsonify(status="ERROR", reason="Uploaded file is empty."), 400

        filename = uploaded_file.filename or "medical_record"
        mime_type = uploaded_file.mimetype or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        record_hash = compute_sha256(original_bytes)
        ciphertext, key, iv = encrypt_file(original_bytes)
        filepath = STORAGE_DIR / f"{record_id}.enc"

        with open(filepath, "wb") as f:
            f.write(ciphertext)

        try:
            conn = get_connection()
            conn.execute("""
                INSERT INTO records
                (record_id, patient_id, doctor_id, title, original_filename, mime_type,
                 encrypted_filepath, aes_key, iv, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (record_id, patient_id, doctor_id, title, filename, mime_type,
                  str(filepath), key, iv, time.time()))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            if filepath.exists():
                filepath.unlink()
            return jsonify(status="ERROR", reason=f"Record ID '{record_id}' already exists."), 409

        # Solidity transaction: only hash + metadata goes on-chain.
        receipt = create_record(record_id, patient_id, doctor_id, title, record_hash)
        return jsonify({
            "status": "SUCCESS",
            "record_id": record_id,
            "record_hash": record_hash,
            "block": block_number(receipt),
            "transaction_hash": tx_hash(receipt),
        }), 201

    except Exception as e:
        print("UPLOAD ERROR:", repr(e))
        return jsonify(status="ERROR", reason=str(e)), 500


@app.post("/grant-access")
def grant():
    try:
        data = request.get_json(force=True)
        patient_id = data["patient_id"]
        doctor_id = data["doctor_id"]
        record_id = data["record_id"]
        duration_hours = float(data.get("duration_hours", 24))
        if duration_hours <= 0:
            return jsonify(status="ERROR", reason="Duration must be positive."), 400

        conn = get_connection()
        row = conn.execute(
            "SELECT record_id FROM records WHERE record_id=? AND patient_id=?",
            (record_id, patient_id),
        ).fetchone()
        conn.close()
        if not row:
            return jsonify(status="ERROR", reason="Record not found for this patient."), 404

        receipt = grant_access(patient_id, doctor_id, record_id, int(duration_hours * 3600))
        allowed, valid_until = check_permission(patient_id, doctor_id, record_id)
        return jsonify({
            "status": "SUCCESS",
            "block": block_number(receipt),
            "transaction_hash": tx_hash(receipt),
            "valid_until": valid_until,
            "allowed": allowed,
        }), 200
    except Exception as e:
        print("GRANT ERROR:", repr(e))
        return jsonify(status="ERROR", reason=str(e)), 500


@app.post("/revoke-access")
def revoke():
    try:
        data = request.get_json(force=True)
        patient_id = data["patient_id"]
        doctor_id = data["doctor_id"]
        record_id = data["record_id"]
        receipt = revoke_access(patient_id, doctor_id, record_id)
        return jsonify({
            "status": "SUCCESS",
            "block": block_number(receipt),
            "transaction_hash": tx_hash(receipt),
        }), 200
    except Exception as e:
        print("REVOKE ERROR:", repr(e))
        return jsonify(status="ERROR", reason=str(e)), 500


@app.post("/view-record")
def view_record():
    try:
        data = request.get_json(force=True)
        patient_id = data["patient_id"]
        doctor_id = data["doctor_id"]
        record_id = data["record_id"]

        allowed, valid_until = check_permission(patient_id, doctor_id, record_id)
        if not allowed:
            return jsonify(status="FORBIDDEN", reason="No valid blockchain authorization (or permission expired/revoked)."), 403

        onchain = get_record(record_id)
        if not onchain[6]:
            return jsonify(status="NOT_FOUND", reason="Record not found on blockchain."), 404
        expected_hash = "0x" + bytes(onchain[4]).hex()

        conn = get_connection()
        row = conn.execute("""
            SELECT encrypted_filepath, aes_key, iv, original_filename, mime_type
            FROM records WHERE record_id=? AND patient_id=?
        """, (record_id, patient_id)).fetchone()
        conn.close()
        if not row:
            return jsonify(status="NOT_FOUND", reason="Off-chain record metadata missing."), 404

        filepath, key, iv, filename, mime_type = row
        if not os.path.exists(filepath):
            return jsonify(status="NOT_FOUND", reason="Encrypted medical file missing."), 404

        with open(filepath, "rb") as f:
            ciphertext = f.read()

        try:
            decrypted = decrypt_file(ciphertext, bytes(key), bytes(iv))
        except Exception as e:
            print("DECRYPTION ERROR:", repr(e))
            return jsonify(status="DECRYPTION_FAILED", reason="Unable to decrypt the medical record."), 500

        current_hash = "0x" + compute_sha256(decrypted)
        if current_hash.lower() != expected_hash.lower():
            return jsonify({
                "status": "INTEGRITY_COMPROMISED",
                "alert": "Decrypted file does not match the SHA-256 fingerprint stored in Solidity.",
                "expected_hash": expected_hash,
                "current_hash": current_hash,
            }), 409

        content = ""
        if mime_type.startswith("text/") or filename.lower().endswith((".txt", ".csv", ".json")):
            content = decrypted.decode("utf-8", errors="ignore")

        return jsonify({
            "status": "AUTHORIZED",
            "integrity": "VERIFIED",
            "record_hash": expected_hash,
            "filename": filename,
            "mime_type": mime_type,
            "content": content,
            "file_base64": base64.b64encode(decrypted).decode("utf-8"),
            "valid_until": valid_until,
        }), 200

    except Exception as e:
        print("VIEW ERROR:", repr(e))
        return jsonify(status="ERROR", reason=str(e)), 500


@app.get("/blockchain")
def blockchain():
    try:
        return jsonify({
            "status": "SUCCESS",
            "ethereum_block": get_block_number(),
            "records": explorer_data(),
        })
    except Exception as e:
        return jsonify(status="ERROR", reason=str(e)), 500


if __name__ == "__main__":
    print("Patient-Centric Decentralized EHR - Solidity backend")
    app.run(host="127.0.0.1", port=5000, debug=False)
