"""
Database layer for Financial Records System — v2
发票上传 + 报销审批流
SQLite with manual SQL — no ORM.
"""
import sqlite3
import os
import json
from contextlib import contextmanager
from typing import Optional

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "finance.db")


def get_connection() -> sqlite3.Connection:
    """Create a new database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema — v2."""
    with get_db() as conn:
        # ── 收支记录表 ────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type VARCHAR(10) NOT NULL CHECK(type IN ('income', 'expense')),
                amount DECIMAL(15,2) NOT NULL CHECK(amount > 0),
                category VARCHAR(50) NOT NULL,
                description TEXT,
                record_date DATE NOT NULL,
                counterparty VARCHAR(100),
                invoice_id INTEGER,
                status VARCHAR(20) DEFAULT 'confirmed' CHECK(status IN ('pending', 'confirmed', 'cancelled')),
                created_by VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_type ON records(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_category ON records(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_date ON records(record_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_status ON records(status)")

        # ── 发票表 ─────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number VARCHAR(50) NOT NULL UNIQUE,
                invoice_type VARCHAR(20) NOT NULL,
                amount DECIMAL(15,2) NOT NULL CHECK(amount > 0),
                tax_amount DECIMAL(15,2),
                issuer VARCHAR(100) NOT NULL,
                issue_date DATE NOT NULL,
                file_path VARCHAR(255),
                remarks TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number)")

        # ── 报销申请表 ──────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reimbursements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                applicant VARCHAR(50) NOT NULL,
                department VARCHAR(50) NOT NULL,
                amount DECIMAL(15,2) NOT NULL CHECK(amount > 0),
                reason TEXT NOT NULL,
                expense_date DATE NOT NULL,
                invoice_ids TEXT,
                status VARCHAR(20) DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'paid')),
                approver VARCHAR(50),
                approved_at DATETIME,
                comment TEXT,
                remarks TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reimb_applicant ON reimbursements(applicant)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reimb_status ON reimbursements(status)")