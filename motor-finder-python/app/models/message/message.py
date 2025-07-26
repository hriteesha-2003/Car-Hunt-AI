from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from bson import ObjectId

class MessageModel(BaseModel):
    sender: str
    receiver: str
    message: str
    file_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    read: bool = False

# To return messages with ID in response
class MessageOut(BaseModel):
    id: str
    sender: str
    receiver: str
    message: str
    timestamp: datetime
    read: bool
