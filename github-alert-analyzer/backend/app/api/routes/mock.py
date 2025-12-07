"""Mock data endpoints for testing without database."""
from fastapi import APIRouter
from datetime import datetime, timedelta
from app.core.security import create_access_token
from app.api.schemas import TokenResponse, UserResponse

router = APIRouter(prefix="/mock", tags=["Mock Data"])


# Mock test user
MOCK_USER = {
    "id": "user_test_123",
    "email": "test@example.com",
    "full_name": "Test User",
    "is_active": True,
    "is_verified": True,
    "subscription_tier": "free",
    "github_connected": True,
    "created_at": datetime.utcnow(),
}


@router.post("/login", response_model=TokenResponse)
async def mock_login():
    """
    Mock login endpoint - returns a test user without database.
    
    Use this to test the frontend:
    - Email: test@example.com
    - Password: (any password works)
    """
    access_token = create_access_token(
        data={"sub": MOCK_USER["id"], "email": MOCK_USER["email"]}
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**MOCK_USER)
    )


@router.get("/dashboard/stats")
async def mock_dashboard_stats():
    """Mock dashboard statistics."""
    return {
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


@router.get("/repositories")
async def mock_repositories():
    """Mock repositories list."""
    return {
        "repositories": [
            {
                "id": 1,
                "name": "frontend-app",
                "full_name": "testuser/frontend-app",
                "description": "React frontend application",
                "language": "JavaScript",
                "stars": 45,
                "open_alerts": 12,
                "last_synced": (datetime.utcnow() - timedelta(hours=2)).isoformat()
            },
            {
                "id": 2,
                "name": "backend-api",
                "full_name": "testuser/backend-api",
                "description": "Python FastAPI backend",
                "language": "Python",
                "stars": 32,
                "open_alerts": 8,
                "last_synced": (datetime.utcnow() - timedelta(hours=5)).isoformat()
            },
            {
                "id": 3,
                "name": "mobile-app",
                "full_name": "testuser/mobile-app",
                "description": "React Native mobile app",
                "language": "JavaScript",
                "stars": 18,
                "open_alerts": 15,
                "last_synced": (datetime.utcnow() - timedelta(days=1)).isoformat()
            }
        ],
        "total": 3
    }


@router.get("/alerts")
async def mock_alerts():
    """Mock alerts list."""
    base_time = datetime.utcnow()
    
    return {
        "alerts": [
            {
                "id": 1,
                "repository_name": "frontend-app",
                "package_name": "axios",
                "severity": "high",
                "state": "open",
                "summary": "Server-Side Request Forgery in axios",
                "description": "Axios NPM package versions before 1.6.0 are vulnerable to Server-Side Request Forgery",
                "ecosystem": "npm",
                "vulnerable_version": "0.21.1",
                "patched_version": "1.6.0",
                "created_at": (base_time - timedelta(days=3)).isoformat(),
                "ghsa_id": "GHSA-wf5p-g6vw-rhxx"
            },
            {
                "id": 2,
                "repository_name": "backend-api",
                "package_name": "fastapi",
                "severity": "critical",
                "state": "open",
                "summary": "Path Traversal in FastAPI",
                "description": "FastAPI versions before 0.100.0 are vulnerable to path traversal attacks",
                "ecosystem": "pip",
                "vulnerable_version": "0.68.0",
                "patched_version": "0.100.0",
                "created_at": (base_time - timedelta(days=5)).isoformat(),
                "ghsa_id": "GHSA-qf9m-vfgh-m389"
            },
            {
                "id": 3,
                "repository_name": "frontend-app",
                "package_name": "react-dom",
                "severity": "medium",
                "state": "open",
                "summary": "XSS vulnerability in react-dom",
                "description": "Cross-site scripting vulnerability in server-side rendering",
                "ecosystem": "npm",
                "vulnerable_version": "17.0.2",
                "patched_version": "18.2.0",
                "created_at": (base_time - timedelta(days=7)).isoformat(),
                "ghsa_id": "GHSA-xxxx-yyyy-zzzz"
            },
            {
                "id": 4,
                "repository_name": "backend-api",
                "package_name": "sqlalchemy",
                "severity": "high",
                "state": "dismissed",
                "summary": "SQL Injection in SQLAlchemy",
                "description": "Potential SQL injection when using raw SQL statements",
                "ecosystem": "pip",
                "vulnerable_version": "1.4.25",
                "patched_version": "2.0.0",
                "created_at": (base_time - timedelta(days=10)).isoformat(),
                "ghsa_id": "GHSA-abcd-efgh-ijkl"
            },
            {
                "id": 5,
                "repository_name": "mobile-app",
                "package_name": "lodash",
                "severity": "critical",
                "state": "open",
                "summary": "Prototype Pollution in lodash",
                "description": "Versions of lodash before 4.17.21 are vulnerable to prototype pollution",
                "ecosystem": "npm",
                "vulnerable_version": "4.17.15",
                "patched_version": "4.17.21",
                "created_at": (base_time - timedelta(days=2)).isoformat(),
                "ghsa_id": "GHSA-p6mc-m468-83gw"
            }
        ],
        "total": 5,
        "page": 1,
        "page_size": 50
    }


@router.get("/alerts/{alert_id}")
async def mock_alert_detail(alert_id: int):
    """Mock individual alert details."""
    return {
        "id": alert_id,
        "repository_name": "frontend-app",
        "package_name": "axios",
        "severity": "high",
        "state": "open",
        "summary": "Server-Side Request Forgery in axios",
        "description": "Axios NPM package versions before 1.6.0 are vulnerable to Server-Side Request Forgery (SSRF) attacks. An attacker can manipulate the URL to make requests to internal services.",
        "ecosystem": "npm",
        "vulnerable_version": "0.21.1",
        "patched_version": "1.6.0",
        "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
        "ghsa_id": "GHSA-wf5p-g6vw-rhxx",
        "cve_id": "CVE-2023-45857",
        "cvss_score": 7.5,
        "cwe_ids": ["CWE-918"],
        "references": [
            "https://github.com/advisories/GHSA-wf5p-g6vw-rhxx",
            "https://nvd.nist.gov/vuln/detail/CVE-2023-45857"
        ],
        "analysis": {
            "analyzed_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
            "model": "claude-3-5-sonnet-20241022",
            "risk_assessment": "HIGH",
            "recommendation": "Upgrade axios to version 1.6.0 or later immediately. This vulnerability allows attackers to bypass URL validation and make requests to internal services.",
            "false_positive_likelihood": "LOW",
            "reasoning": "This is a legitimate security concern. The package is widely used and the vulnerability affects request handling logic."
        }
    }
