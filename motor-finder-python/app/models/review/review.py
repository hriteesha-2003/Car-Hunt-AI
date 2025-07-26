from pydantic import BaseModel, Field
from typing import Optional

class CarReview(BaseModel):
    car_id: str
    rating: float = Field(..., ge=1.0, le=5.0)
    review: Optional[str] = None
