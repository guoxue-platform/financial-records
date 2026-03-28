"""
Financial Records System — FastAPI Backend v2
收支记账系统 + 发票上传 + 报销审批流
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import date, datetime
import json

from database import init_db, get_db
from models import (
    RecordCreate, RecordUpdate, RecordResponse, SummaryResponse,
    InvoiceCreate, InvoiceResponse,
    ReimbursementCreate, ReimbursementApprove, ReimbursementResponse,
    MonthlyData, CategoryAnalysisResponse, CategoryData,
    ReimbSummaryResponse,
)

app = FastAPI(title="财务记账系统 API v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ═══════════════════════════════════════════════════════════════
# 收支记录 API
# ═══════════════════════════════════════════════════════════════

@app.post("/api/records", response_model=RecordResponse, status_code=201)
def create_record(payload: RecordCreate):
    """新增一条收支记录"""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO records (type, amount, category, description, record_date,
                                 counterparty, invoice_id, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
            """,
            (
                payload.type, payload.amount, payload.category, payload.description,
                payload.record_date.isoformat(), payload.counterparty,
                payload.invoice_id, payload.created_by,
            ),
        )
        record_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    return _record_row_to_resp(row)


@app.get("/api/records", response_model=List[RecordResponse])
def list_records(
    record_type: Optional[str] = Query(None, alias="type"),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """获取收支记录列表"""
    if record_type and record_type not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="无效的 type 值")
    if status and status not in ("pending", "confirmed", "cancelled"):
        raise HTTPException(status_code=400, detail="无效的 status 值")

    query = "SELECT * FROM records WHERE is_deleted = 0"
    params: list = []
    if record_type:
        query += " AND type = ?"; params.append(record_type)
    if category:
        query += " AND category = ?"; params.append(category)
    if status:
        query += " AND status = ?"; params.append(status)
    if start_date:
        query += " AND record_date >= ?"; params.append(start_date.isoformat())
    if end_date:
        query += " AND record_date <= ?"; params.append(end_date.isoformat())
    query += " ORDER BY record_date DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_record_row_to_resp(row) for row in rows]


@app.get("/api/records/summary", response_model=SummaryResponse)
def get_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """收支汇总统计"""
    where = "WHERE is_deleted = 0 AND status = 'confirmed'"
    params: list = []
    if start_date:
        where += " AND record_date >= ?"; params.append(start_date.isoformat())
    if end_date:
        where += " AND record_date <= ?"; params.append(end_date.isoformat())

    with get_db() as conn:
        income_row = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as cnt FROM records {where} AND type = 'income'",
            params,
        ).fetchone()
        expense_row = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as cnt FROM records {where} AND type = 'expense'",
            params,
        ).fetchone()
        cat_rows = conn.execute(
            f"SELECT type, category, SUM(amount) as total FROM records {where} GROUP BY type, category ORDER BY type, total DESC",
            params,
        ).fetchall()

    by_category = {}
    for row in cat_rows:
        by_category.setdefault(row["type"], []).append({"category": row["category"], "total": round(row["total"], 2)})

    return SummaryResponse(
        total_income=round(income_row["total"], 2),
        total_expense=round(expense_row["total"], 2),
        net_balance=round(income_row["total"] - expense_row["total"], 2),
        income_count=income_row["cnt"],
        expense_count=expense_row["cnt"],
        by_category=by_category,
    )


@app.get("/api/records/monthly", response_model=List[MonthlyData])
def get_monthly_report(
    year: Optional[int] = Query(None, description="筛选年份，如 2026"),
):
    """按月汇总统计"""
    where = "WHERE is_deleted = 0 AND status = 'confirmed'"
    params: list = []
    if year:
        where += " AND strftime('%Y', record_date) = ?"
        params.append(str(year))

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT
                strftime('%Y-%m', record_date) as year_month,
                type,
                SUM(amount) as total,
                COUNT(*) as cnt
            FROM records {where}
            GROUP BY year_month, type
            ORDER BY year_month DESC
            """,
            params,
        ).fetchall()

    monthly_map: dict = {}
    for row in rows:
        ym = row["year_month"]
        if ym not in monthly_map:
            monthly_map[ym] = {"income": 0.0, "expense": 0.0, "income_count": 0, "expense_count": 0}
        if row["type"] == "income":
            monthly_map[ym]["income"] = round(row["total"], 2)
            monthly_map[ym]["income_count"] = row["cnt"]
        else:
            monthly_map[ym]["expense"] = round(row["total"], 2)
            monthly_map[ym]["expense_count"] = row["cnt"]

    result = []
    for ym, v in sorted(monthly_map.items(), reverse=True):
        result.append(MonthlyData(
            year_month=ym,
            income=v["income"],
            expense=v["expense"],
            net=round(v["income"] - v["expense"], 2),
            income_count=v["income_count"],
            expense_count=v["expense_count"],
        ))
    return result


@app.get("/api/records/category-analysis", response_model=CategoryAnalysisResponse)
def get_category_analysis(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """类别分析（占比）"""
    where = "WHERE is_deleted = 0 AND status = 'confirmed'"
    params: list = []
    if start_date:
        where += " AND record_date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        where += " AND record_date <= ?"
        params.append(end_date.isoformat())

    with get_db() as conn:
        income_rows = conn.execute(
            f"SELECT category, SUM(amount) as total FROM records {where} AND type = 'income' GROUP BY category ORDER BY total DESC",
            params,
        ).fetchall()
        expense_rows = conn.execute(
            f"SELECT category, SUM(amount) as total FROM records {where} AND type = 'expense' GROUP BY category ORDER BY total DESC",
            params,
        ).fetchall()
        income_total = sum(r["total"] for r in income_rows)
        expense_total = sum(r["total"] for r in expense_rows)

    income_data = [
        CategoryData(category=r["category"], amount=round(r["total"], 2),
                      proportion=round(r["total"] / income_total * 100, 2) if income_total else 0)
        for r in income_rows
    ]
    expense_data = [
        CategoryData(category=r["category"], amount=round(r["total"], 2),
                      proportion=round(r["total"] / expense_total * 100, 2) if expense_total else 0)
        for r in expense_rows
    ]
    return CategoryAnalysisResponse(income=income_data, expense=expense_data)


@app.get("/api/reimbursements/summary", response_model=ReimbSummaryResponse)
def get_reimb_summary(
    department: Optional[str] = Query(None),
):
    """报销统计汇总"""
    where = "WHERE is_deleted = 0"
    params: list = []
    if department:
        where += " AND department = ?"
        params.append(department)

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT status, SUM(amount) as total, COUNT(*) as cnt FROM reimbursements {where} GROUP BY status",
            params,
        ).fetchall()
        dept_rows = conn.execute(
            f"SELECT department, SUM(amount) as total, COUNT(*) as cnt FROM reimbursements {where} GROUP BY department ORDER BY total DESC",
            params,
        ).fetchall()

    status_map = {r["status"]: {"cnt": r["cnt"], "total": r["total"]} for r in rows}
    total_count = sum(s["cnt"] for s in status_map.values())
    total_amount = sum(s["total"] for s in status_map.values())

    return ReimbSummaryResponse(
        total_count=total_count,
        pending_count=status_map.get("pending", {"cnt": 0})["cnt"],
        approved_count=status_map.get("approved", {"cnt": 0})["cnt"],
        rejected_count=status_map.get("rejected", {"cnt": 0})["cnt"],
        paid_count=status_map.get("paid", {"cnt": 0})["cnt"],
        total_amount=round(total_amount, 2),
        pending_amount=round(status_map.get("pending", {"total": 0})["total"], 2),
        approved_amount=round(status_map.get("approved", {"total": 0})["total"], 2),
        paid_amount=round(status_map.get("paid", {"total": 0})["total"], 2),
        by_department=[
            {"department": r["department"], "count": r["cnt"], "total": round(r["total"], 2)}
            for r in dept_rows
        ],
    )


@app.get("/api/records/{record_id}", response_model=RecordResponse)
def get_record(record_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM records WHERE id = ? AND is_deleted = 0", (record_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return _record_row_to_resp(row)


@app.put("/api/records/{record_id}", response_model=RecordResponse)
def update_record(record_id: int, payload: RecordUpdate):
    updates, params = [], []
    for field, val in [
        ("type", payload.type), ("amount", payload.amount), ("category", payload.category),
        ("description", payload.description), ("record_date", payload.record_date),
        ("counterparty", payload.counterparty), ("invoice_id", payload.invoice_id), ("status", payload.status),
    ]:
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(val.isoformat() if hasattr(val, "isoformat") else round(val, 2) if isinstance(val, float) else val)
    if not updates:
        raise HTTPException(status_code=400, detail="没有提供更新字段")
    params.append(record_id)
    with get_db() as conn:
        conn.execute(f"UPDATE records SET {', '.join(updates)} WHERE id = ? AND is_deleted = 0", params)
        row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return _record_row_to_resp(row)


@app.delete("/api/records/{record_id}", status_code=204)
def delete_record(record_id: int):
    with get_db() as conn:
        cursor = conn.execute("UPDATE records SET is_deleted = 1 WHERE id = ? AND is_deleted = 0", (record_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="记录不存在")


def list_categories():
    with get_db() as conn:
        income_cats = conn.execute("SELECT DISTINCT category FROM records WHERE type = 'income' AND is_deleted = 0").fetchall()
        expense_cats = conn.execute("SELECT DISTINCT category FROM records WHERE type = 'expense' AND is_deleted = 0").fetchall()
    return {"income": [r["category"] for r in income_cats], "expense": [r["category"] for r in expense_cats]}


# ═══════════════════════════════════════════════════════════════
# 发票 API
# ═══════════════════════════════════════════════════════════════

@app.post("/api/invoices", response_model=InvoiceResponse, status_code=201)
def create_invoice(payload: InvoiceCreate):
    """新增发票记录"""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO invoices (invoice_number, invoice_type, amount, tax_amount, issuer,
                                   issue_date, file_path, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.invoice_number, payload.invoice_type, payload.amount,
                payload.tax_amount, payload.issuer, payload.issue_date.isoformat(),
                payload.file_path, payload.remarks,
            ),
        )
        invoice_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    return _invoice_row_to_resp(row)


@app.get("/api/invoices", response_model=List[InvoiceResponse])
def list_invoices(
    invoice_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """获取发票列表"""
    query = "SELECT * FROM invoices WHERE is_deleted = 0"
    params: list = []
    if invoice_type:
        query += " AND invoice_type = ?"; params.append(invoice_type)
    if start_date:
        query += " AND issue_date >= ?"; params.append(start_date.isoformat())
    if end_date:
        query += " AND issue_date <= ?"; params.append(end_date.isoformat())
    query += " ORDER BY issue_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_invoice_row_to_resp(row) for row in rows]


@app.get("/api/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ? AND is_deleted = 0", (invoice_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="发票不存在")
    return _invoice_row_to_resp(row)


@app.put("/api/invoices/{invoice_id}/upload", response_model=InvoiceResponse)
def upload_invoice_file(invoice_id: int, file_path: str = Query(..., description="发票文件路径")):
    """更新发票文件路径"""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE invoices SET file_path = ? WHERE id = ? AND is_deleted = 0",
            (file_path, invoice_id),
        )
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="发票不存在")
    return _invoice_row_to_resp(row)


# ═══════════════════════════════════════════════════════════════
# 报销 API
# ═══════════════════════════════════════════════════════════════

@app.post("/api/reimbursements", response_model=ReimbursementResponse, status_code=201)
def create_reimbursement(payload: ReimbursementCreate):
    """提交报销申请"""
    invoice_ids_json = json.dumps(payload.invoice_ids) if payload.invoice_ids else None
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reimbursements (applicant, department, amount, reason, expense_date,
                                        invoice_ids, status, remarks)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                payload.applicant, payload.department, payload.amount, payload.reason,
                payload.expense_date.isoformat(), invoice_ids_json, payload.remarks,
            ),
        )
        reimb_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM reimbursements WHERE id = ?", (reimb_id,)).fetchone()
    return _reimb_row_to_resp(row)


@app.get("/api/reimbursements", response_model=List[ReimbursementResponse])
def list_reimbursements(
    status: Optional[str] = Query(None),
    applicant: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """获取报销申请列表"""
    if status and status not in ("pending", "approved", "rejected", "paid"):
        raise HTTPException(status_code=400, detail="无效的 status 值")
    query = "SELECT * FROM reimbursements WHERE is_deleted = 0"
    params: list = []
    if status:
        query += " AND status = ?"; params.append(status)
    if applicant:
        query += " AND applicant = ?"; params.append(applicant)
    if department:
        query += " AND department = ?"; params.append(department)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_reimb_row_to_resp(row) for row in rows]


@app.get("/api/reimbursements/{reimb_id}", response_model=ReimbursementResponse)
def get_reimbursement(reimb_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reimbursements WHERE id = ? AND is_deleted = 0", (reimb_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="报销申请不存在")
    return _reimb_row_to_resp(row)


@app.post("/api/reimbursements/{reimb_id}/approve", response_model=ReimbursementResponse)
def approve_reimbursement(reimb_id: int, payload: ReimbursementApprove):
    """审批报销申请"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reimbursements WHERE id = ? AND is_deleted = 0", (reimb_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="报销申请不存在")
    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail="只能审批待处理的申请")
    with get_db() as conn:
        conn.execute(
            """
            UPDATE reimbursements SET status = 'approved', approver = ?, approved_at = ?,
            comment = ? WHERE id = ? AND is_deleted = 0
            """,
            (payload.approver, datetime.now().isoformat(), payload.comment, reimb_id),
        )
        row = conn.execute("SELECT * FROM reimbursements WHERE id = ?", (reimb_id,)).fetchone()
    return _reimb_row_to_resp(row)


@app.post("/api/reimbursements/{reimb_id}/reject", response_model=ReimbursementResponse)
def reject_reimbursement(reimb_id: int, payload: ReimbursementApprove):
    """驳回报销申请"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reimbursements WHERE id = ? AND is_deleted = 0", (reimb_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="报销申请不存在")
    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail="只能驳回待处理的申请")
    with get_db() as conn:
        conn.execute(
            """
            UPDATE reimbursements SET status = 'rejected', approver = ?, approved_at = ?,
            comment = ? WHERE id = ? AND is_deleted = 0
            """,
            (payload.approver, datetime.now().isoformat(), payload.comment, reimb_id),
        )
        row = conn.execute("SELECT * FROM reimbursements WHERE id = ?", (reimb_id,)).fetchone()
    return _reimb_row_to_resp(row)


@app.post("/api/reimbursements/{reimb_id}/pay", response_model=ReimbursementResponse)
def pay_reimbursement(reimb_id: int, payer: str = Query(..., description="付款人")):
    """确认付款（标记为已付款）"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reimbursements WHERE id = ? AND is_deleted = 0", (reimb_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="报销申请不存在")
    if row["status"] != "approved":
        raise HTTPException(status_code=400, detail="只能对待已审批的申请付款")
    with get_db() as conn:
        conn.execute(
            "UPDATE reimbursements SET status = 'paid' WHERE id = ? AND is_deleted = 0",
            (reimb_id,),
        )
        row = conn.execute("SELECT * FROM reimbursements WHERE id = ?", (reimb_id,)).fetchone()
    return _reimb_row_to_resp(row)


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _record_row_to_resp(row) -> RecordResponse:
    return RecordResponse(
        id=row["id"], type=row["type"], amount=row["amount"],
        category=row["category"], description=row["description"],
        record_date=row["record_date"], counterparty=row["counterparty"],
        invoice_id=row["invoice_id"], status=row["status"],
        created_by=row["created_by"], created_at=row["created_at"],
    )

def _invoice_row_to_resp(row) -> InvoiceResponse:
    return InvoiceResponse(
        id=row["id"], invoice_number=row["invoice_number"],
        invoice_type=row["invoice_type"], amount=row["amount"],
        tax_amount=row["tax_amount"], issuer=row["issuer"],
        issue_date=row["issue_date"], file_path=row["file_path"],
        remarks=row["remarks"], created_at=row["created_at"],
    )

def _reimb_row_to_resp(row) -> ReimbursementResponse:
    invoice_ids = json.loads(row["invoice_ids"]) if row["invoice_ids"] else None
    return ReimbursementResponse(
        id=row["id"], applicant=row["applicant"], department=row["department"],
        amount=row["amount"], reason=row["reason"], expense_date=row["expense_date"],
        invoice_ids=invoice_ids, status=row["status"], approver=row["approver"],
        approved_at=row["approved_at"], comment=row["comment"],
        remarks=row["remarks"], created_at=row["created_at"],
    )