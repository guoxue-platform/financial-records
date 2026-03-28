"""
初始化示例数据 — v2：收支 + 发票 + 报销
"""
from database import init_db, get_db
import json

# 发票示例
SAMPLE_INVOICES = [
    {
        "invoice_number": "FP2026030001",
        "invoice_type": "增值税普通发票",
        "amount": 50000.00,
        "tax_amount": 5000.00,
        "issuer": "A公司",
        "issue_date": "2026-03-20",
        "file_path": "/invoices/FP2026030001.pdf",
        "remarks": "产品X订单",
    },
    {
        "invoice_number": "FP2026030015",
        "invoice_type": "增值税专用发票",
        "amount": 15000.00,
        "tax_amount": 1500.00,
        "issuer": "XX物业",
        "issue_date": "2026-03-01",
        "file_path": "/invoices/FP2026030015.pdf",
        "remarks": "3月办公室租金",
    },
]

# 报销示例
SAMPLE_REIMBURSEMENTS = [
    {
        "applicant": "李研发",
        "department": "研发部",
        "amount": 3200.00,
        "reason": "北京出差异地调试设备，交通及住宿费用",
        "expense_date": "2026-03-10",
        "invoice_ids": json.dumps([]),
        "status": "approved",
        "approver": "王总监",
        "approved_at": "2026-03-12 10:00:00",
        "comment": "同意报销",
        "remarks": "出差审批单已签字",
    },
    {
        "applicant": "张市场",
        "department": "市场部",
        "amount": 5800.00,
        "reason": "客户招待费，拜访上海B公司",
        "expense_date": "2026-03-18",
        "invoice_ids": json.dumps([]),
        "status": "pending",
        "approver": None,
        "approved_at": None,
        "comment": None,
        "remarks": "待审批",
    },
]

# 收支记录示例（与v1一致）
SAMPLE_RECORDS = [
    {
        "type": "income",
        "amount": 50000.00,
        "category": "收入-产品销售",
        "description": "收到A公司货款，产品X订单完成交付",
        "record_date": "2026-03-20",
        "counterparty": "A公司",
        "invoice_id": 1,
        "status": "confirmed",
        "created_by": "王财务",
    },
    {
        "type": "expense",
        "amount": 15000.00,
        "category": "支出-办公租金",
        "description": "3月份办公室租金",
        "record_date": "2026-03-01",
        "counterparty": "XX物业",
        "invoice_id": 2,
        "status": "confirmed",
        "created_by": "王财务",
    },
    {
        "type": "expense",
        "amount": 8500.00,
        "category": "支出-人员工资",
        "description": "研发部3月工资发放",
        "record_date": "2026-03-15",
        "counterparty": "员工工资户",
        "invoice_id": None,
        "status": "confirmed",
        "created_by": "李人事",
    },
]


def seed_data():
    init_db()
    with get_db() as conn:
        for inv in SAMPLE_INVOICES:
            conn.execute(
                """INSERT INTO invoices (invoice_number, invoice_type, amount, tax_amount,
                                        issuer, issue_date, file_path, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (inv["invoice_number"], inv["invoice_type"], inv["amount"], inv["tax_amount"],
                 inv["issuer"], inv["issue_date"], inv["file_path"], inv["remarks"]),
            )
        for reimb in SAMPLE_REIMBURSEMENTS:
            conn.execute(
                """INSERT INTO reimbursements (applicant, department, amount, reason, expense_date,
                                              invoice_ids, status, approver, approved_at, comment, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (reimb["applicant"], reimb["department"], reimb["amount"], reimb["reason"],
                 reimb["expense_date"], reimb["invoice_ids"], reimb["status"],
                 reimb["approver"], reimb["approved_at"], reimb["comment"], reimb["remarks"]),
            )
        for rec in SAMPLE_RECORDS:
            conn.execute(
                """INSERT INTO records (type, amount, category, description, record_date,
                                       counterparty, invoice_id, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rec["type"], rec["amount"], rec["category"], rec["description"],
                 rec["record_date"], rec["counterparty"], rec["invoice_id"], rec["status"], rec["created_by"]),
            )
    print(f"✅ 发票 {len(SAMPLE_INVOICES)} 条 | 报销 {len(SAMPLE_REIMBURSEMENTS)} 条 | 收支 {len(SAMPLE_RECORDS)} 条")


if __name__ == "__main__":
    seed_data()