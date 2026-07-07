from pydantic import BaseModel, EmailStr, Field, field_validator
import re

class RegisterDTO(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    first_name: str = Field(min_length=2, max_length=50)
    last_name: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=50)

    @field_validator('username')
    @classmethod
    def validate_username(cls, value: str):
        if not re.fullmatch(r'[A-Za-z0-9]+', value):
            raise ValueError('Username may contain only letters and digits')
        return value

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, value: str):
        if not re.fullmatch(r'[A-Za-z-]+', value):
            raise ValueError('Name contains invalid characters')
        return value.strip()

    @field_validator('password')
    @classmethod
    def validate_password(cls, value: str):
        if not re.search(r'[A-Z]', value):
            raise ValueError('Password must contain an uppercase')
        if not re.search(r'[a-z]', value):
            raise ValueError('Password must contain a lowercase')
        if not re.search(r'\d', value):
            raise ValueError('Password must contain a digit')
        if not re.search(r'[!@#$%^&*.?]', value):
            raise ValueError('Password must contain a special character')
        return value