from pydantic import BaseModel


# Schema to represent JWT token to user
class AuthToken(BaseModel):
    jwt_token: str