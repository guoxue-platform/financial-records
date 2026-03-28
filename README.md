# 财务记账系统 (Financial Records System) v2

[![CI](https://github.com/guoxue-platform/financial-records/actions/workflows/ci.yml/badge.svg)](https://github.com/guoxue-platform/financial-records/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

内部收支记账工具，支持发票管理与报销审批流。

## 功能模块

| 模块 | 说明 |
|------|------|
| 收支记录 | 收入/支出登记，支持分类统计、月度汇总、往来单位管理 |
| 发票管理 | 增值税发票管理，支持文件路径关联 |
| 报销审批流 | 申请→审批→付款三阶段，状态全程可追溯 |

## 快速启动

### 本地开发

```bash
cd backend
pip install -r requirements.txt
python init_sample_data.py   # 初始化示例数据（已有数据可跳过）
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

API 文档：http://localhost:8001/docs

### Docker 部署

```bash
docker build -t financial-records .
docker run -d -p 8001:8001 \
  --env-file backend/.env.example \
  financial-records
```

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | finance.db | 数据库路径（容器内相对路径） |
| PORT | 8001 | 服务端口 |
| CORS_ORIGINS | * | CORS 白名单 |
| LOG_LEVEL | INFO | 日志级别 |

## API 概览

### 收支记录（9个端点）

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

### 发票管理（4个端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/invoices | 新增发票 |
| GET | /api/invoices | 发票列表 |
| GET | /api/invoices/{id} | 发票详情 |
| PUT | /api/invoices/{id}/upload | 更新发票文件路径 |

### 报销审批流（7个端点）

状态流转：`pending` → `approved` / `rejected` → `paid`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/reimbursements | 提交报销申请 |
| GET | /api/reimbursements | 报销列表 |
| GET | /api/reimbursements/{id} | 报销详情 |
| POST | /api/reimbursements/{id}/approve | 审批通过 |
| POST | /api/reimbursements/{id}/reject | 审批驳回 |
| POST | /api/reimbursements/{id}/pay | 确认付款 |
| GET | /api/reimbursements/summary | 报销统计汇总 |

## 数据模型

### 收支记录

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | income / expense |
| amount | float | 金额（精确到分） |
| category | string | 类别 |
| description | string | 描述/备注 |
| record_date | date | 记录日期 |
| counterparty | string | 对方单位/个人 |
| invoice_id | string | 关联发票ID |
| status | string | pending / confirmed / cancelled |
| created_by | string | 创建人 |

### 发票

| 字段 | 类型 | 说明 |
|------|------|------|
| invoice_number | string | 发票号码（唯一） |
| invoice_type | string | 专票/普票/电子发票/其他 |
| amount | float | 发票金额 |
| tax_amount | float | 税额 |
| issuer | string | 开票单位 |
| issue_date | date | 开票日期 |
| file_path | string | 发票文件路径 |
| remarks | string | 备注 |

### 报销

| 字段 | 类型 | 说明 |
|------|------|------|
| applicant | string | 申请人 |
| department | string | 部门 |
| amount | float | 报销金额 |
| reason | string | 报销事由 |
| expense_date | date | 费用发生日期 |
| invoice_ids | list | 关联发票ID列表 |
| status | string | pending / approved / rejected / paid |
| approver | string | 审批人 |
| approved_at | datetime | 审批时间 |
| comment | string | 审批意见 |

## 示例数据

**发票（2条）：**
- FP2026030001 | 增值税普通发票 | ¥50,000 | A公司
- FP2026030015 | 增值税专用发票 | ¥15,000 | XX物业

**报销（2条）：**
- 李研发 | ¥3,200 | 已审批 | 出差异地调试设备
- 张市场 | ¥5,800 | 待审批 | 客户招待费

**收支（3条）：**
- 收入 ¥50,000 | 产品销售 | A公司
- 支出 ¥15,000 | 办公租金 | XX物业
- 支出 ¥8,500 | 人员工资 | 员工工资户

## 技术栈

- **后端**：Python 3.11+ / FastAPI / Pydantic
- **数据库**：SQLite（本地文件，无外部依赖）
- **部署**：Docker / uvicorn
- **CI/CD**：GitHub Actions（pip install → 服务验证）

## 目录结构

```
financial-records/
├── .github/workflows/ci.yml   # GitHub Actions CI
├── backend/
│   ├── main.py                # FastAPI 入口
│   ├── models.py              # Pydantic 数据模型
│   ├── database.py            # SQLite 操作层
│   ├── init_sample_data.py    # 示例数据初始化
│   ├── requirements.txt        # Python 依赖
│   ├── .env.example            # 环境变量示例
│   └── finance.db             # SQLite 数据库（已 .gitignore）
├── Dockerfile                  # Docker 镜像构建
├── .dockerignore
├── .gitignore
├── LICENSE                     # MIT License
└── README.md
```

## CI/CD

每次 push 到 `main` 分支自动触发：

1. 安装依赖（`pip install -r requirements.txt`）
2. 初始化示例数据
3. 启动服务并验证可访问性

---

**仓库**：https://github.com/guoxue-platform/financial-records
