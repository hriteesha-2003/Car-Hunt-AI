from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

# Handle MongoDB ObjectId in Pydantic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# The EmailTemplate schema
class EmailTemplate(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    template_type: str = Field(..., max_length=50)
    subject: str = Field(..., max_length=255)
    html_content: str
    is_active: bool = True
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "template_type": "password",
                "subject": "Reset Password for {{username}}",
                "html_content": "<p>Your new password is: {{password}}</p>",
                "is_active": True
            }
        }
