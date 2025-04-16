from datetime import datetime, timedelta
from typing import Any, Union
from passlib.context import CryptContext

import jwt

from src.core import config
from src.services.gatekeeper_service import GatekeeperServiceClient

pwd_context = CryptContext(schemes=[config.CRYPT_CONTEXT_SCHEME])


def create_access_token(data: Union[str, Any], expire_time) -> str:
    if expire_time:
        expire = datetime.utcnow() + expire_time
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=int(60 * 24 * 8)
        )
    to_encode = {"exp": expire, "sub": str(data)}
    encoded_jwt = jwt.encode(payload=to_encode, key=config.KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


async def create_gk_jwt_tokens() -> Union[str, str]:
    token, refresh = await GatekeeperServiceClient.gk_get_jwt_token()
    return token, refresh

