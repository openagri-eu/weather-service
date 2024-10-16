from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed
from pydantic import EmailStr, Field



class User(Document):
    id: UUID = Field(default_factory=uuid4)
    email: Annotated[str, Indexed(EmailStr, unique=True)]
    password: str
    first_name: str | None = None
    last_name: str | None = None
    disabled: bool = False

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "id": "2a6aef88-a821-48c0-867c-a66f192c1132",
                "email": "user@mail.org",
                "password": "1234",
                "disabled": True,
            }
        }

    class Settings:
        name = "users"