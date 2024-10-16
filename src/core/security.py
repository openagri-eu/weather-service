from passlib.context import CryptContext

import jwt

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"])


def hash_password(password: str) -> str:
    return pwd_context.hash(password)
