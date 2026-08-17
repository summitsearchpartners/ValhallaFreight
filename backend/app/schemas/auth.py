from pydantic import BaseModel, Field
from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    # Keep login identifiers flexible during local development. Production users can
    # still use normal email addresses, while the seeded *.local account remains valid.
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: str
    active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
