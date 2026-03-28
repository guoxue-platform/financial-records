"""
Pydantic models for Financial Records System — v2
发票上传 + 报销审批流
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import date, datetime


# ─── 收支记录 Models ────────────────────────────────────────

class RecordCreate(BaseModel):
    type: Literal["income", "expense"]
    amount: float = Field(..., gt=0, description="金额，必须大于0")
    category: str = Field(..., min_length=1, max_length=50, description="类别")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    record_date: date = Field(..., description="记录日期")
    counterparty: Optional[str] = Field(None, max_length=100, description="对方单位/个人")
    invoice_id: Optional[int] = Field(None, description="关联发票ID")
    created_by: str = Field(..., min_length=1, max_length=50, description="创建人")

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("金额必须大于0")
        return round(v, 2)

    @field_validator("category")
    @classmethod
    def category_strip(cls, v: str) -> str:
        return v.strip()


class RecordUpdate(BaseModel):
    type: Optional[Literal["income", "expense"]] = None
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    record_date: Optional[date] = None
    counterparty: Optional[str] = Field(None, max_length=100)
    invoice_id: Optional[int] = None
    status: Optional[Literal["pending", "confirmed", "cancelled"]] = None


class RecordResponse(BaseModel):
    id: int
    type: str
    amount: float
    category: str
    description: Optional[str]
    record_date: str
    counterparty: Optional[str]
    invoice_id: Optional[int]
    status: str
    created_by: str
    created_at: str


class SummaryResponse(BaseModel):
    total_income: float
    total_expense: float
    net_balance: float
    income_count: int
    expense_count: int
    by_category: dict


# ─── 发票 Models ────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    invoice_number: str = Field(..., min_length=1, max_length=50, description="发票号码")
    invoice_type: Literal["增值税专用发票", "增值税普通发票", "电子发票", "其他"] = Field(..., description="发票类型")
    amount: float = Field(..., gt=0, description="发票金额")
    tax_amount: Optional[float] = Field(None, ge=0, description="税额")
    issuer: str = Field(..., min_length=1, max_length=100, description="开票单位")
    issue_date: date = Field(..., description="开票日期")
    file_path: Optional[str] = Field(None, max_length=255, description="发票文件路径")
    remarks: Optional[str] = Field(None, max_length=500, description="备注")

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        return round(v, 2)


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    invoice_type: str
    amount: float
    tax_amount: Optional[float]
    issuer: str
    issue_date: str
    file_path: Optional[str]
    remarks: Optional[str]
    created_at: str


# ─── 报销 Models ─────────────────────────────────────────────

class ReimbursementCreate(BaseModel):
    applicant: str = Field(..., min_length=1, max_length=50, description="申请人")
    department: str = Field(..., min_length=1, max_length=50, description="部门")
    amount: float = Field(..., gt=0, description="报销金额")
    reason: str = Field(..., min_length=1, max_length=500, description="报销事由")
    expense_date: date = Field(..., description="费用发生日期")
    invoice_ids: Optional[list[int]] = Field(None, description="关联发票ID列表")
    remarks: Optional[str] = Field(None, max_length=500, description="备注")


class ReimbursementApprove(BaseModel):
    approver: str = Field(..., min_length=1, max_length=50, description="审批人")
    comment: Optional[str] = Field(None, max_length=200, description="审批意见")


class ReimbursementResponse(BaseModel):
    id: int
    applicant: str
    department: str
    amount: float
    reason: str
    expense_date: str
    invoice_ids: Optional[list[int]]
    status: Literal["pending", "approved", "rejected", "paid"]
    approver: Optional[str]
    approved_at: Optional[str]
    comment: Optional[str]
    remarks: Optional[str]
    created_at: str


# ─── 统计报表 Models ─────────────────────────────────────────

class MonthlyData(BaseModel):
    year_month: str
    income: float
    expense: float
    net: float
    income_count: int
    expense_count: int


class CategoryData(BaseModel):
    category: str
    amount: float
    proportion: float


class CategoryAnalysisResponse(BaseModel):
    income: list[CategoryData]
    expense: list[CategoryData]


class ReimbSummaryResponse(BaseModel):
    total_count: int
    pending_count: int
    approved_count: int
    rejected_count: int
    paid_count: int
    total_amount: float
    pending_amount: float
    approved_amount: float
    paid_amount: float
    by_department: list[dict]