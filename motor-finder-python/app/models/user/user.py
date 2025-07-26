from enum import Enum
from pydantic import BaseModel, EmailStr, Field, constr


# Define available roles using Enum
class Role(str, Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    USER = "user"
    AGENT = "agent"
    FREELANCER = "freelancer"
    BUYER = "buyer"
    CLIENT = "client"

class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class User(BaseModel):
    role: Role = Field(..., description="Role")
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., description="Password")
    
class ForgotPasswordRequest(BaseModel):
    username: str 
    
class reset_password(BaseModel):
    username: str
    temporary_password: str
    new_password: str
   