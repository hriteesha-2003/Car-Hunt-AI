# models/privacy.py
from pydantic import BaseModel

class PrivacyPolicy(BaseModel):
    introduction: str
    info_collected: str
    info_sources: str
    info_processing: str

    
