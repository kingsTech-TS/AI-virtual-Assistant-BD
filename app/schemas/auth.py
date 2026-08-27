import re
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

_MATRIC_NUMBER_RE = re.compile(r"^\d{9}$")


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8)
    matric_number: str
    department_id: Optional[PyObjectId] = None
    faculty: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("matric_number")
    @classmethod
    def validate_matric_number(cls, v: str) -> str:
        if not _MATRIC_NUMBER_RE.match(v.strip()):
            raise ValueError("Matric number must contain exactly 9 digits")
        return v.strip()


class StaffRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    staff_id: str = Field(..., min_length=2, max_length=50)
    department_id: Optional[PyObjectId] = None
    faculty: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=30)
    position: Optional[str] = Field(None, max_length=100)

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
