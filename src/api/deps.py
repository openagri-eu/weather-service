from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException


from src.models.user import User


reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token/")


async def current_user() -> Optional[User]:
    user = await User.find().first_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not exist in db!")
    return user
