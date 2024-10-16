from pydantic import BaseModel, EmailStr


# User register and login auth
class UserAuth(BaseModel):
    email: EmailStr
    password: str


# User field returned to client
class UserOut(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


# User updatable fields
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None