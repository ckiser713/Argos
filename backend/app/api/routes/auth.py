from __future__ import annotations

from datetime import timedelta

from app.services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    # In a real app, you'd verify the user's credentials here
    # For now, we'll just create a token for the provided username
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": form_data.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}
