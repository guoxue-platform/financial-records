# 财务记账系统 (Financial Records System) v2

内部收支记账工具 + 发票管理 + 报销审批流。

[![CI](https://github.com/guoxue-platform/financial-records/actions/workflows/ci.yml/badge.svg)](https://github.com/guoxue-platform/financial-records/actions)

**GitHub 仓库：** https://github.com/guoxue-platform/financial-records

## 目录结构

```
financial-records/
├── .gitignore
├── README.md
└── backend/
    ├── .env.example        # 环境变量示例
    ├── main.py             # FastAPI 入口
    ├── models.py            # Pydantic 数据模型
    ├── database.py          # SQLite 操作层
    ├── init_sample_data.py  # 示例数据初始化
    ├── finance.db           # SQLite 数据库文件（已初始化）
    ├── requirements.txt     # Python 依赖
    └── venv/               # Python 虚拟环境（勿提交）
```

## 快速启动

```bash
cd backend
pip install --break-system-packages -r requirements.txt
python3 init_sample_data.py   # 初始化示例数据（已完成）
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

API 文档：http://localhost:8001/docs

## 环境变量

复制 `.env.example` 为 `.env` 并按需修改：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | finance.db | 数据库路径 |
| PORT | 8001 | 服务端口 |
| CORS_ORIGINS | * | CORS 白名单 |
| LOG_LEVEL | INFO | 日志级别 |

## 三大模块

### 1. 收支记录

| 字段 | 说明 |
|------|------|
| type | income（收入）/ expense（支出） |
| amount | 金额，精确到分 |
| category | 类别 |
| description | 描述/备注 |
| record_date | 记录日期 |
| counterparty | 对方单位/个人 |
| invoice_id | 关联发票ID |
| status | pending / confirmed / cancelled |
| created_by | 创建人 |

### 2. 发票管理

| 字段 | 说明 |
|------|------|
| invoice_number | 发票号码（唯一） |
| invoice_type | 增值税专用发票 / 普通发票 / 电子发票 / 其他 |
| amount | 发票金额 |
| tax_amount | 税额 |
| issuer | 开票单位 |
| issue_date | 开票日期 |
| file_path | 发票文件路径 |
| remarks | 备注 |

### 3. 报销审批流

**状态流转：** `pending` → `approved` / `rejected` → `paid`

| 字段 | 说明 |
|------|------|
| applicant | 申请人 |
| department | 部门 |
| amount | 报销金额 |
| reason | 报销事由 |
| expense_date | 费用发生日期 |
| invoice_ids | 关联发票ID列表 |
| status | pending / approved / rejected / paid |
| approver | 审批人 |
| approved_at | 审批时间 |
| comment | 审批意见 |

## API 端点

### 收支记录
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/records | 新增记录 |
| GET | /api/records | 列表（支持筛选） |
| GET | /api/records/summary | 汇总统计 |
| GET | /api/records/monthly | 月度汇总 |
| GET | /api/records/category-analysis | 类别分析（占比） |
| GET | /api/records/{id} | 详情 |
| PUT | /api/records/{id} | 更新 |
| DELETE | /api/records/{id} | 删除 |
| GET | /api/categories | 已用类别列表 |

### 发票
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/invoices | 新增发票 |
| GET | /api/invoices | 发票列表 |
| GET | /api/invoices/{id} | 发票详情 |
| PUT | /api/invoices/{id}/upload | 更新发票文件路径 |

### 报销
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/reimbursements | 提交报销申请 |
| GET | /api/reimbursements | 报销列表 |
| GET | /api/reimbursements/{id} | 报销详情 |
| POST | /api/reimbursements/{id}/approve | 审批通过 |
| POST | /api/reimbursements/{id}/reject | 审批驳回 |
| POST | /api/reimbursements/{id}/pay | 确认付款 |
| GET | /api/reimbursements/summary | 报销统计汇总 |

## 示例数据

**发票（2条）：**
1. FP2026030001 | 增值税普通发票 | ¥50,000 | A公司
2. FP2026030015 | 增值税专用发票 | ¥15,000 | XX物业

**报销（2条）：**
1. 李研发 | ¥3,200 | 已审批 | 出差异地调试设备
2. 张市场 | ¥5,800 | 待审批 | 客户招待费

**收支（3条）：**
1. 收入 ¥50,000 | 产品销售 | A公司
2. 支出 ¥15,000 | 办公租金 | XX物业
3. 支出 ¥8,500 | 人员工资 | 员工工资户

## 技术栈

- Python + FastAPI + SQLite
- 无前端（纯API，可对接现有前端框架）
