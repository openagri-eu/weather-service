from datetime import timedelta
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.api.deps import current_user
from src.core import config
from src.core.security import create_access_token, hash_password
from src.models.user import User
from src.schemas.user import UserAuth, UserOut, UserUpdate
from src.schemas.auth import AuthToken


logger = logging.getLogger(__name__)

user_router = APIRouter(prefix="/user", tags=["User"])


@user_router.post("/register", response_model=UserOut, response_model_exclude_none=True)
async def register(request: Request, user_auth: UserAuth):
    user = await request.app.dao.find_user_by_email(user_auth.email)
    if user:
        raise HTTPException(status.HTTP_409_CONFLICT, "User with that email already exists")
    hashed_password = hash_password(user_auth.password)
    user = await User(email=user_auth.email, password=hashed_password).create()
    return user

@user_router.get("", response_model=UserOut, response_model_exclude_none=True)
async def get_user(user: User =  Depends(current_user)):
   return user

@user_router.patch("", response_model=UserOut, response_model_exclude_none=True)
async def update_user(user_update: UserUpdate, user: User =  Depends(current_user)):
   user.email = user_update.email
   user.save()
   return user

@user_router.post("/login", response_model=AuthToken)
async def login(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await request.app.dao.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expire_time=access_token_expires
    )

    return AuthToken(jwt_token=access_token)

