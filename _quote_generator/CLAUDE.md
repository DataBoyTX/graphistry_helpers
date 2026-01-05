# Claude Context - Quote Generator Web App

This file contains context for Claude to continue working on this project.

---

## Project Overview

A multi-user web application for generating quotes and order forms with Google Drive/Gmail integration.

---

## Current Status

### Completed (Phases 1-3 + partial Phase 4-5)

- **Backend (FastAPI)**
  - SQLAlchemy models: users, customers, products, quotes, quote_line_items, orders, approval_settings
  - Alembic migrations configured and run
  - All REST API endpoints implemented
  - JWT authentication with httpOnly cookies
  - Google OAuth flow (needs Google Cloud credentials to test)
  - Dev login bypass for testing (`POST /auth/dev-login`)
  - PDF generation with WeasyPrint
  - Dashboard stats endpoint

- **Frontend (React + Vite + TypeScript)**
  - Tailwind CSS styling
  - React Query for data fetching
  - All pages: Dashboard, Customers, Products, Quotes, Orders, Settings, Login
  - Quote builder component
  - Auth hook with dev login support

### Not Yet Implemented

- Google Drive upload integration (service exists but not wired up)
- Gmail draft creation (service exists but not wired up)
- HTML quote templates (US + International)
- Docker configuration
- PostgreSQL production setup
- Tests

---

## How to Run

### Backend

```bash
cd backend

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at http://localhost:8000
API docs at http://localhost:8000/docs

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at http://localhost:5173
Proxies API requests to backend at :8000

### Testing Without Google OAuth

1. Start backend in development mode (default)
2. Go to http://localhost:5173/login
3. Click "Dev Login (Test User)" button
4. This creates a test@example.com admin user and logs you in

---

## Known Issues & Fixes Applied

### 1. Alembic Async Driver Error
**Error**: `InvalidRequestError: The asyncio extension requires an async driver`
**Fix**: Modified `backend/alembic/env.py` to use synchronous `create_engine` instead of async

### 2. WeasyPrint/pydyf Compatibility
**Error**: `TypeError: PDF.__init__() takes 1 positional argument but 3 were given`
**Fix**: Upgrade packages: `pip install 'weasyprint>=61.0' 'pydyf>=0.11.0'`

### 3. User Role Enum vs String
**Error**: `AttributeError: 'str' object has no attribute 'value'`
**Location**: `backend/app/routers/auth.py` dev_login endpoint
**Fix**: Added isinstance check: `user.role if isinstance(user.role, str) else user.role.value`

### 4. User is_active Field NULL
**Issue**: New users created without is_active set, causing 401 errors
**Fix**: Ensure User model defaults is_active=True (already in model, but manual DB fix was needed for existing data)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + Vite + TypeScript |
| UI | Tailwind CSS |
| Backend | FastAPI (Python 3.11+) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy (async) |
| Auth | Google OAuth 2.0 + JWT |
| PDF | WeasyPrint |
| Google APIs | google-api-python-client |

---

## Database Schema

### Users
- id, email, name, google_id, role (admin/user)
- google_access_token, google_refresh_token, google_token_expiry
- picture_url, is_active, created_at, updated_at

### Customers
- id, company_name, contact_name, email, phone
- address_line1, address_line2, city, state, postal_code, country
- tax_id, is_international, created_by, created_at, updated_at

### Products
- id, sku, name, description, category
- unit_price, currency, is_recurring, billing_period
- is_active, created_at, updated_at

### Quotes
- id, quote_number (Q-YYYY-NNNN), customer_id, created_by, status
- subtotal, discount_percent, discount_amount, tax_rate, tax_amount, total, currency
- template_type, terms_and_conditions, notes, valid_until
- requires_approval, approved_by, approved_at
- drive_file_id, drive_pdf_id, gmail_draft_id
- created_at, updated_at, sent_at

### Quote Line Items
- id, quote_id, product_id, description
- quantity, unit_price, discount_percent, line_total, sort_order

### Orders
- id, order_number (O-YYYY-NNNN), quote_id, customer_id
- status, accepted_at, accepted_by
- subtotal, discount_amount, tax_amount, total, currency, notes

### Approval Settings
- id, threshold_amount, require_approval_international, updated_by, updated_at

---

## API Endpoints

### Authentication
- `GET /auth/google` - Get Google OAuth URL
- `GET /auth/google/callback` - OAuth callback
- `GET /auth/me` - Get current user
- `POST /auth/logout` - Logout
- `POST /auth/dev-login` - Dev-only login bypass

### Customers
- `GET /customers` - List (paginated)
- `POST /customers` - Create
- `GET /customers/{id}` - Get
- `PUT /customers/{id}` - Update
- `DELETE /customers/{id}` - Delete

### Products
- `GET /products` - List
- `POST /products` - Create
- `GET /products/{id}` - Get
- `PUT /products/{id}` - Update
- `DELETE /products/{id}` - Delete

### Quotes
- `GET /quotes` - List
- `POST /quotes` - Create
- `GET /quotes/{id}` - Get with line items
- `PUT /quotes/{id}` - Update
- `DELETE /quotes/{id}` - Delete (draft only)
- `POST /quotes/{id}/submit` - Submit for approval
- `POST /quotes/{id}/approve` - Approve (admin)
- `POST /quotes/{id}/reject` - Reject (admin)
- `POST /quotes/{id}/accept` - Convert to order
- `GET /quotes/{id}/pdf` - Download PDF

### Orders
- `GET /orders` - List
- `GET /orders/{id}` - Get
- `PATCH /orders/{id}/status` - Update status

### Dashboard
- `GET /dashboard/stats` - Statistics

---

## Next Steps (Phase 4-6)

1. Create HTML quote templates (US + International variants)
2. Wire up Google Drive upload in quote send flow
3. Wire up Gmail draft creation
4. Add Docker configuration
5. Set up PostgreSQL for production
6. Write tests
7. Add approval workflow UI improvements
8. Add quote history/audit trail

---

## File Structure

```
quote-generator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── database.py          # DB session
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── routers/             # API routes
│   │   └── services/            # Business logic
│   ├── alembic/                 # Migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/api.ts
│   │   └── types/
│   └── package.json
├── .gitignore
├── CLAUDE.md                    # This file
└── README.md
```
