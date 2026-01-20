"""API dependencies for authentication and authorization."""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.user_service import user_service
from app.core.security import decode_access_token


security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> Any:
    """Get the current authenticated user from JWT token or Firebase token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    
    user = await user_service.get(token_data.user_id)
    
    if user is None:
        # If user doesn't exist in our Firestore but has a valid Firebase token,
        # we might want to auto-create them or just fail.
        # For now, we fail to ensure they go through registration.
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current active user."""
    return current_user


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_active_user)]
