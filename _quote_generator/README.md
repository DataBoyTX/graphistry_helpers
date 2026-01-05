# Quote Generator

A multi-user web application for generating professional quotes and order forms.

## Features

- Customer management
- Product catalog
- Quote creation with line items
- PDF generation
- Quote workflow (draft → pending → approved → sent → accepted)
- Order creation from accepted quotes
- Dashboard with statistics
- Google OAuth authentication
- Google Drive/Gmail integration (planned)

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and click "Dev Login" to test.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite/PostgreSQL
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Auth**: Google OAuth 2.0, JWT
- **PDF**: WeasyPrint

## API Documentation

With the backend running, visit http://localhost:8000/docs for interactive API docs.
