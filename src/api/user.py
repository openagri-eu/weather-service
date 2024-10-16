import logging

from fastapi import APIRouter, Depends, Request, HTTPException

from src.api.deps import current_user
from src.core.security import hash_password
from src.models.user import User
from src.schemas.user import UserAuth, UserOut


logger = logging.getLogger(__name__)

user_router = APIRouter(prefix="/user", tags=["User"])


@user_router.post("/register", response_model=UserOut, response_model_exclude_none=True)
async def register(request: Request, user_auth: UserAuth):
    user = await request.app.dao.find_user_by_email(user_auth.email)
    if user:
        raise HTTPException(409, "User with that email already exists")
    hashed_password = hash_password(user_auth.password)
    user = await User(email=user_auth.email, password=hashed_password).create()
    return user

@user_router.get("", response_model=UserOut, response_model_exclude_none=True)
async def get_user(user: User =  Depends(current_user)):
   return user

