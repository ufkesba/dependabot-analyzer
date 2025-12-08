"""Authentication API routes."""
import httpx
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
)
from app.models import User, OAuthConnection
from app.api.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.api.deps import CurrentUser


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email}
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Generate token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email}
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: CurrentUser):
    """Refresh access token."""
    access_token = create_access_token(
        data={"sub": current_user.id, "email": current_user.email}
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(current_user)
    )


@router.get("/github/login")
async def github_login():
    """Redirect to GitHub OAuth authorization page."""
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured"
        )
    
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_redirect_uri}"
        f"&scope=read:user,user:email,repo"
    )
    
    return {"auth_url": github_auth_url}


@router.get("/github/callback")
async def github_callback(code: str, db: Session = Depends(get_db)):
    """Handle GitHub OAuth callback."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured"
        )
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received from GitHub"
            )
        
        # Get user info from GitHub
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )
        
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from GitHub"
            )
        
        github_user = user_response.json()
        
        # Get primary email if not public
        email = github_user.get("email")
        if not email:
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )
            if emails_response.status_code == 200:
                emails = emails_response.json()
                primary_email = next((e for e in emails if e.get("primary")), None)
                if primary_email:
                    email = primary_email.get("email")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No email found in GitHub account"
            )
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user
            user = User(
                email=email,
                full_name=github_user.get("name"),
                is_verified=True,  # GitHub email is verified
                password_hash="",  # No password for OAuth users
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Store or update OAuth connection
        oauth_conn = db.query(OAuthConnection).filter(
            OAuthConnection.user_id == user.id,
            OAuthConnection.provider == "github"
        ).first()
        
        if oauth_conn:
            # Update existing connection
            oauth_conn.access_token = access_token
            oauth_conn.provider_user_id = str(github_user.get("id"))
            oauth_conn.scopes = "read:user,user:email,repo"
            oauth_conn.profile_data = json.dumps(github_user)
        else:
            # Create new connection
            oauth_conn = OAuthConnection(
                user_id=user.id,
                provider="github",
                provider_user_id=str(github_user.get("id")),
                access_token=access_token,
                scopes="read:user,user:email,repo",
                profile_data=json.dumps(github_user)
            )
            db.add(oauth_conn)
        
        db.commit()
        
        # Create our app's access token
        app_access_token = create_access_token(
            data={"sub": user.id, "email": user.email}
        )
        
        return TokenResponse(
            access_token=app_access_token,
            user=UserResponse.model_validate(user)
        )
