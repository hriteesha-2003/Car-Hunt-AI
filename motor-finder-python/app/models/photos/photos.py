from pydantic import BaseModel, Field
from typing import Optional

class Photos(BaseModel):
    company_id: str
    photo_url: str
    uploaded_at: str
