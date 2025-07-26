from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId   


class AddAIAgent(BaseModel):
    place_of_appear: str

class  AIAgentResponse(BaseModel):
   id: str
   place_of_appear: str
   ai_model_file_url: str
    