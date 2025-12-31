# Quote Generator

A modern web application for generating professional quotes and order forms with Google Drive and Gmail integration.

## Features

- **Multi-user Authentication** - Google OAuth with role-based access (Admin/User)
- **Customer Management** - Store and manage customer information
- **Product Catalog** - Manage products with categories, pricing, and billing periods
- **Quote Generation** - Create professional quotes with line items, discounts, and taxes
- **Order Tracking** - Convert accepted quotes to orders and track fulfillment
- **Approval Workflow** - Optional approval for quotes over threshold or international
- **US & International Templates** - Different tax handling (Sales Tax vs VAT)
- **Multi-Currency Support** - USD, EUR, GBP, and more
- **Google Integration** - Save quotes to Drive (PDF + Doc) and create Gmail drafts

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI (Python 3.11+), SQLAlchemy, Pydantic |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | Google OAuth 2.0 |
| PDF | WeasyPrint |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud Console project with OAuth credentials

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your Google OAuth credentials

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable these APIs:
   - Google+ API (for login)
   - Google Drive API
   - Gmail API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:8000/auth/google/callback`
5. Copy Client ID and Client Secret to your `.env` file

## Configuration

### Environment Variables (backend/.env)

```env
# Required
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
SECRET_KEY=generate-with-openssl-rand-hex-32

# Optional
DATABASE_URL=sqlite+aiosqlite:///./quote_generator.db
FRONTEND_URL=http://localhost:5173
DEFAULT_QUOTE_VALIDITY_DAYS=30
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
quote-generator/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── config.py        # Settings
│   │   ├── database.py      # DB connection
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── routers/         # API routes
│   │   └── services/        # Business logic
│   ├── alembic/             # Migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom hooks
│   │   ├── services/        # API client
│   │   └── types/           # TypeScript types
│   └── package.json
└── README.md
```

## Development Roadmap

### Phase 1: Foundation (Complete)
- [x] Backend project structure
- [x] SQLAlchemy models
- [x] Alembic migrations
- [x] Google OAuth authentication
- [x] User/Customer/Product/Quote/Order APIs
- [x] React frontend with routing

### Phase 2: Core Features (Next)
- [ ] Quote line item editor
- [ ] Google Sheets product import
- [ ] Quote PDF generation

### Phase 3: Google Integration
- [ ] Google Drive upload
- [ ] Gmail draft creation
- [ ] Quote email templates

### Phase 4: Polish
- [ ] Dashboard statistics
- [ ] Quote status tracking
- [ ] Approval workflow UI

### Phase 5: Production
- [ ] Docker configuration
- [ ] PostgreSQL setup
- [ ] Deployment docs

## License

Private - All rights reserved
