# Quick Start - Testing Without Database

The backend is now running with mock data - no database needed!

## 🚀 Backend (Running on port 8000)

The backend is already running with mock endpoints at: http://localhost:8000

### Mock Test User Credentials

Use this endpoint to get a test user token:

```bash
curl -X POST http://localhost:8000/api/mock/login
```

**Test User Details:**
- Email: `test@example.com`
- ID: `user_test_123`
- Name: Test User
- Subscription: Free tier
- Status: Active & Verified

The login returns a JWT token you can use for authenticated requests.

### Available Mock Endpoints

1. **Mock Login** (no password needed)
   ```
   POST /api/mock/login
   ```

2. **Dashboard Stats**
   ```
   GET /api/mock/dashboard/stats
   ```

3. **Repositories List**
   ```
   GET /api/mock/repositories
   ```

4. **Alerts List**
   ```
   GET /api/mock/alerts
   ```

5. **Alert Details**
   ```
   GET /api/mock/alerts/{id}
   ```

### API Documentation

Visit http://localhost:8000/docs to see interactive API docs (Swagger UI)

## 🎨 Frontend Setup

1. Make sure the frontend is configured to use the mock endpoint:

```bash
cd frontend

# Create .env.local if it doesn't exist
cat > .env.local << 'ENVEOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=true
ENVEOF

# Start the frontend
npm run dev
```

2. Open http://localhost:3000

3. For the login page, you can either:
   - Use the mock endpoint by modifying the frontend to call `/api/mock/login` 
   - Or temporarily bypass auth to test the dashboard

## 🧪 Testing the App

### Test the backend directly:

```bash
# Get mock login token
TOKEN=$(curl -s -X POST http://localhost:8000/api/mock/login | jq -r '.access_token')

# Get dashboard stats
curl -s http://localhost:8000/api/mock/dashboard/stats | jq

# Get repositories
curl -s http://localhost:8000/api/mock/repositories | jq

# Get alerts
curl -s http://localhost:8000/api/mock/alerts | jq

# Get specific alert
curl -s http://localhost:8000/api/mock/alerts/1 | jq
```

### Sample Response - Dashboard Stats:
```json
{
  "total_alerts": 47,
  "critical_alerts": 8,
  "high_alerts": 15,
  "medium_alerts": 18,
  "low_alerts": 6,
  "alerts_by_ecosystem": {
    "npm": 25,
    "pip": 12,
    "maven": 6,
    "composer": 4
  },
  "alerts_by_state": {
    "open": 35,
    "dismissed": 8,
    "fixed": 4
  },
  "recent_analyses": 12
}
```

### Sample Response - Alerts:
The mock data includes 5 sample alerts with different severities:
- Critical: lodash prototype pollution
- High: axios SSRF, SQLAlchemy SQL injection  
- Medium: react-dom XSS
- With analysis, CVE IDs, GHSA IDs, and more

## 📝 Notes

- The backend is running WITHOUT a database connection
- All data is mocked and in-memory
- Perfect for frontend development and UI testing
- When you're ready for real data, set up Supabase (see SETUP_GUIDE.md)

## 🔗 GitHub OAuth (Optional)

To test GitHub OAuth login without setting up a real OAuth app, you can continue using mock mode. 

If you want to set up real GitHub OAuth:

1. **Create GitHub OAuth App:**
   - Go to https://github.com/settings/developers
   - Click "New OAuth App"
   - Application name: `GitHub Alert Analyzer`
   - Homepage URL: `http://localhost:3000`
   - Callback URL: `http://localhost:3000/auth/callback/github`

2. **Add credentials to backend/.env:**
   ```env
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   GITHUB_REDIRECT_URI=http://localhost:3000/auth/callback/github
   ```

3. **Restart backend** and test:
   - Login with demo mode
   - Go to Dashboard → Settings
   - Click "Connect GitHub Account"
   - Authorize on GitHub
   - You'll be redirected back and authenticated!

## 🛑 Stopping the Servers

```bash
# Stop backend
lsof -ti:8000 | xargs kill -9

# Stop frontend
lsof -ti:3000 | xargs kill -9
```

