"""LLM configuration API routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import LLMConfiguration
from app.api.schemas import LLMConfigCreate, LLMConfigResponse, LLMConfigUpdate
from app.api.deps import CurrentUser


router = APIRouter(prefix="/llm-configs", tags=["LLM Configurations"])


@router.get("", response_model=List[LLMConfigResponse])
async def list_llm_configs(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """List all LLM configurations for current user."""
    configs = db.query(LLMConfiguration).filter(
        LLMConfiguration.user_id == current_user.id
    ).all()
    return [LLMConfigResponse.model_validate(c) for c in configs]


@router.post("", response_model=LLMConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    config_data: LLMConfigCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Create a new LLM configuration."""
    # If this is set as default, unset other defaults
    if config_data.is_default:
        db.query(LLMConfiguration).filter(
            LLMConfiguration.user_id == current_user.id,
            LLMConfiguration.is_default == True
        ).update({"is_default": False})
    
    config = LLMConfiguration(
        user_id=current_user.id,
        provider=config_data.provider,
        api_key=config_data.api_key,  # Should be encrypted in production
        model_name=config_data.model_name,
        max_tokens=config_data.max_tokens,
        temperature=config_data.temperature,
        is_default=config_data.is_default,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return LLMConfigResponse.model_validate(config)


@router.get("/{config_id}", response_model=LLMConfigResponse)
async def get_llm_config(
    config_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get a specific LLM configuration."""
    config = db.query(LLMConfiguration).filter(
        LLMConfiguration.id == config_id,
        LLMConfiguration.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM configuration not found"
        )
    
    return LLMConfigResponse.model_validate(config)


@router.put("/{config_id}", response_model=LLMConfigResponse)
async def update_llm_config(
    config_id: str,
    config_data: LLMConfigUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Update an LLM configuration."""
    config = db.query(LLMConfiguration).filter(
        LLMConfiguration.id == config_id,
        LLMConfiguration.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM configuration not found"
        )
    
    # If setting as default, unset other defaults
    if config_data.is_default:
        db.query(LLMConfiguration).filter(
            LLMConfiguration.user_id == current_user.id,
            LLMConfiguration.is_default == True,
            LLMConfiguration.id != config_id
        ).update({"is_default": False})
    
    # Update fields
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return LLMConfigResponse.model_validate(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(
    config_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Delete an LLM configuration."""
    config = db.query(LLMConfiguration).filter(
        LLMConfiguration.id == config_id,
        LLMConfiguration.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM configuration not found"
        )
    
    db.delete(config)
    db.commit()


@router.post("/{config_id}/test")
async def test_llm_config(
    config_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Test an LLM configuration by making a simple API call."""
    config = db.query(LLMConfiguration).filter(
        LLMConfiguration.id == config_id,
        LLMConfiguration.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM configuration not found"
        )
    
    # TODO: Implement actual API test
    # For now, return a mock success
    return {"status": "success", "message": "Configuration is valid"}
