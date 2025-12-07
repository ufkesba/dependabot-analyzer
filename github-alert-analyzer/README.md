# GitHub Alert Analyzer

AI-powered security analysis for GitHub Dependabot alerts. Transform your security alerts into actionable insights with intelligent LLM analysis.

## Features

- 🔐 **Secure Authentication** - Email/password auth with JWT tokens
- 🔗 **GitHub Integration** - OAuth connection to sync repositories and alerts
- 🤖 **AI Analysis** - LLM-powered vulnerability assessment with Claude and GPT
- 📊 **Dashboard** - Real-time overview of alerts by severity, ecosystem, and state
- 🔍 **Advanced Filtering** - Filter by repository, severity, state, and more
- 📈 **Analysis History** - Track and compare analyses over time

## Tech Stack

### Backend
- **FastAPI** (0.115.6) - Modern Python web framework
- **SQLAlchemy** (2.0.36) - Database ORM
- **Supabase** - Managed PostgreSQL database
- **Anthropic/OpenAI** - LLM providers for analysis

### Frontend
- **Next.js** (15.5.7) - React framework with App Router
- **React** (19.0.0) - UI library
- **Tailwind CSS** (3.4.16) - Styling
- **Zustand** (5.0.2) - State management
- **Axios** (1.13.2) - HTTP client

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 22+
- [Supabase Account](https://supabase.com) (free tier available)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your Supabase connection string:
# 1. Go to https://app.supabase.com/project/_/settings/database
# 2. Copy the "Connection string" (Session mode recommended)
# 3. Replace [YOUR-PASSWORD] with your database password
# 4. Update DATABASE_URL in .env

# Run database migrations
alembic upgrade head

# Start the server
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local
# Edit .env.local with your configuration

# Start the development server
npm run dev
```

### Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Project Structure

```
github-alert-analyzer/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes and schemas
│   │   ├── core/          # Core config, security, database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── services/      # Business logic
│   │   └── workers/       # Celery tasks
│   ├── alembic/           # Database migrations
│   ├── tests/             # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities, API client, store
│   │   └── hooks/         # Custom hooks
│   └── package.json
└── scripts/               # Development scripts
```

## Security

All dependencies have been selected for:
- Latest stable versions (December 2024)
- No known critical vulnerabilities
- Active maintenance

Run security audits:

```bash
# Backend
cd backend
pip-audit

# Frontend
cd frontend
npm audit
```

## Environment Variables

See `.env.example` files in both `backend/` and `frontend/` directories for required configuration.

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### Repositories
- `GET /api/repositories` - List repositories
- `POST /api/repositories/sync` - Sync from GitHub
- `GET /api/repositories/:id` - Get repository details

### Alerts
- `GET /api/alerts` - List alerts with filtering
- `GET /api/alerts/:id` - Get alert details
- `POST /api/alerts/:id/analyze` - Request LLM analysis
- `POST /api/alerts/bulk-analyze` - Bulk analysis

### Dashboard
- `GET /api/dashboard/stats` - Dashboard statistics

## License

MIT
