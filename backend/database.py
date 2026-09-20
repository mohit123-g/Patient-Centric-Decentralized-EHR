# import sqlite3
# from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent.parent
# DB_PATH = BASE_DIR / "database.db"


# def get_connection():
#     conn = sqlite3.connect(DB_PATH, timeout=15)
#     conn.execute("PRAGMA busy_timeout = 15000")
#     return conn


# def init_db():
#     conn = get_connection()
#     conn.execute("PRAGMA journal_mode=WAL")
#     conn.execute('''
#         CREATE TABLE IF NOT EXISTS records (
#             record_id TEXT PRIMARY KEY,
#             patient_id TEXT NOT NULL,
#             doctor_id TEXT NOT NULL,
#             title TEXT NOT NULL,
#             original_filename TEXT NOT NULL,
#             mime_type TEXT NOT NULL,
#             encrypted_filepath TEXT NOT NULL,
#             aes_key BLOB NOT NULL,
#             iv BLOB NOT NULL,
#             uploaded_at REAL NOT NULL
#         )
#     ''')
#     conn.commit()
#     conn.close()


import sqlite3
from pathlib import Path


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Open a connection to the SQLite database.

    timeout=15:
        Wait up to 15 seconds if the database is temporarily busy.
    """
    conn = sqlite3.connect(DB_PATH, timeout=15)

    # Allow SQLite to wait when the database is locked.
    conn.execute("PRAGMA busy_timeout = 15000")

    # Return rows that can be accessed by column name if needed.
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """
    Create the records table if it does not exist.

    Also performs a small migration:
    if an older database.db is already present, the new
    document_type / uploaded_by_role / uploaded_by_id columns
    are added automatically.
    """

    conn = get_connection()

    try:
        # Improve SQLite behavior for simultaneous reads/writes.
        conn.execute("PRAGMA journal_mode=WAL")

        # ----------------------------------------------------
        # Create the main records table
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                record_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                title TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                encrypted_filepath TEXT NOT NULL,
                aes_key BLOB NOT NULL,
                iv BLOB NOT NULL,
                uploaded_at REAL NOT NULL,

                document_type TEXT DEFAULT 'Other',
                uploaded_by_role TEXT DEFAULT 'Patient',
                uploaded_by_id TEXT
            )
        """)

        # ----------------------------------------------------
        # Migration support for older database.db files
        # ----------------------------------------------------

        existing_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(records)").fetchall()
        }

        # Add document_type if it is missing
        if "document_type" not in existing_columns:
            conn.execute("""
                ALTER TABLE records
                ADD COLUMN document_type TEXT DEFAULT 'Other'
            """)

        # Add uploaded_by_role if it is missing
        if "uploaded_by_role" not in existing_columns:
            conn.execute("""
                ALTER TABLE records
                ADD COLUMN uploaded_by_role TEXT DEFAULT 'Patient'
            """)

        # Add uploaded_by_id if it is missing
        if "uploaded_by_id" not in existing_columns:
            conn.execute("""
                ALTER TABLE records
                ADD COLUMN uploaded_by_id TEXT
            """)

        # ----------------------------------------------------
        # Save changes
        # ----------------------------------------------------

        conn.commit()

    finally:
        # Always close the database connection.
        conn.close()