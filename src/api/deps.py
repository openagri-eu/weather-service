from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
import jwt
from pydantic import ValidationError


from src.core import config, security
from src.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login")


async def current_user(token: str = Depends(oauth2_scheme)) -> User: # type: ignore
    try:
        decoded_jwt_token = jwt.decode(
            token, config.KEY, algorithms=[security.ALGORITHM]
        )
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = await User.find({"email": decoded_jwt_token["sub"]}).first_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
