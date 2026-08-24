from typing import Any, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.schemas.common import PyObjectId, SuccessResponse
from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8)
    matric_number: str
    department_id: Optional[PyObjectId] = None
    faculty: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(populate_by_name=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int

    model_config = ConfigDict(populate_by_name=True)


class RefreshRequest(BaseModel):
    refresh_token: str

    model_config = ConfigDict(populate_by_name=True)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(populate_by_name=True)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

    model_config = ConfigDict(populate_by_name=True)


class MessageResponseData(BaseModel):
    message: str

    model_config = ConfigDict(populate_by_name=True)


MessageResponse = SuccessResponse[MessageResponseData]

MeResponse = SuccessResponse[UserResponse]
