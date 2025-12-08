# Setup Guide - GitHub Alert Analyzer with Supabase

This guide will help you set up the GitHub Alert Analyzer using Supabase for the database (no local PostgreSQL or Redis needed).

## Prerequisites

- Python 3.11+
- Node.js 22+
- [Supabase Account](https://supabase.com) (free tier available)
- GitHub Account (for OAuth)

## Step 1: Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com) and sign up/login
2. Click "New Project"
3. Choose an organization and fill in:
   - **Project Name**: `github-alert-analyzer`
   - **Database Password**: (save this - you'll need it)
   - **Region**: Choose closest to you
4. Wait for the project to be created (~2 minutes)

## Step 2: Get Supabase Connection String

1. In your Supabase project dashboard, go to **Settings** → **Database**
2. Scroll down to **Connection string**
3. Select the **Session mode** tab
4. Copy the connection string (it looks like):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with the database password you created

## Step 3: Backend Setup

```bash
cd github-alert-analyzer/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env and update DATABASE_URL with your Supabase connection string
# Example:
# DATABASE_URL=postgresql://postgres:your_password@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

### Configure Environment Variables

Edit `backend/.env`:

```env
# Database (Supabase)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
DATABASE_ECHO=False

# Security (generate secure keys for production)
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET=your-jwt-secret-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_REDIRECT_URI=http://localhost:3000/api/auth/callback/github

# LLM Providers
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Environment
ENVIRONMENT=development
DEBUG=True
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

### Run Database Migrations

```bash
# Still in backend directory with venv activated
alembic upgrade head
```

### Start Backend Server

```bash
python -m uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Step 4: Frontend Setup

```bash
cd github-alert-analyzer/frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Edit .env.local with your configuration
```

### Configure Environment Variables

Edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Start Frontend Server

```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Step 5: GitHub OAuth Setup (Optional)

To enable GitHub repository syncing and OAuth login:

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: GitHub Alert Analyzer
   - **Homepage URL**: http://localhost:3000
   - **Authorization callback URL**: http://localhost:3000/auth/callback/github
   - **Scopes**: The app will request `read:user`, `user:email`, and `repo` access
4. Click "Register application"
5. Copy the **Client ID** and generate a **Client Secret**
6. Update your `backend/.env`:
   ```env
   GITHUB_CLIENT_ID=your_client_id_here
   GITHUB_CLIENT_SECRET=your_client_secret_here
   GITHUB_REDIRECT_URI=http://localhost:3000/auth/callback/github
   ```
7. Restart the backend server:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

### Using GitHub OAuth

Once configured, users can:
- Click "Connect GitHub Account" in Dashboard → Settings
- Authorize the app on GitHub
- Automatically login/register with their GitHub account
- Sync repositories and Dependabot alerts

## Step 6: LLM API Keys (Optional)

To enable AI analysis features:

### OpenAI
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Update `backend/.env`:
   ```env
   OPENAI_API_KEY=sk-your-key-here
   ```

### Anthropic (Claude)
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create a new API key
3. Update `backend/.env`:
   ```env
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

## Verification

### Check Backend
```bash
curl http://localhost:8000/docs
# Should open API documentation
```

### Check Frontend
Open http://localhost:3000 in your browser - you should see the landing page

### Check Database Connection
The backend logs should show:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

No database connection errors should appear.

## Troubleshooting

### Backend won't start - Database connection error
- Verify your Supabase connection string is correct in `backend/.env`
- Check that you replaced `[YOUR-PASSWORD]` with your actual password
- Ensure your Supabase project is active and not paused

### Frontend can't connect to backend
- Verify backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Check CORS settings in `backend/.env`

### CORS errors
- Ensure `CORS_ORIGINS` in `backend/.env` includes your frontend URL
- Format should be: `CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]`

## Next Steps

1. Create a user account via the frontend
2. Connect your GitHub account (if OAuth is configured)
3. Sync repositories
4. View and analyze Dependabot alerts

## Production Deployment

For production deployment:

1. **Generate secure secrets**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Use this for `SECRET_KEY` and `JWT_SECRET`

2. **Update CORS_ORIGINS** to include your production domain
3. **Set DEBUG=False** and **ENVIRONMENT=production**
4. **Use Supabase** connection pooling for better performance
5. **Enable SSL** for database connections in production

## Cost Considerations

- **Supabase Free Tier**: 500MB database, 2GB bandwidth/month
- **GitHub OAuth**: Free
- **OpenAI API**: Pay per use (~$0.002/1K tokens for GPT-3.5)
- **Anthropic API**: Pay per use (~$0.003/1K tokens for Claude)

This setup eliminates the need for local PostgreSQL and Redis, making it perfect for development and small production deployments.
