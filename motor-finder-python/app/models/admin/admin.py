import re
from typing import Optional
from fastapi import Form
from pydantic import BaseModel, EmailStr, Field, field_validator

class AddCompany(BaseModel):
  name: str
  about: str
  category_id: str
  subcategory_id: int
  active_status: int
  address: str
  phone_number: str
  email: EmailStr
  currency: str
  pan_no: str = Field(..., description="PAN number")
  gst_no: str = Field(..., description="GST number")
  website: str = Field(..., description="Website")
  logo_url: Optional[str]

  @field_validator("phone_number")
  def validate_phone_number(cls, v):
    regex = r"^[6789]\d{9}$"
    if not re.fullmatch(regex, v):
      raise ValueError(
        "Invalid Indian phone number. Must be 10 digits starting with 6-9."
      )
    return v

  @field_validator("pan_no")
  def validate_pan_no(cls, v):
    regex = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    if not re.fullmatch(regex, v.upper()):
      raise ValueError("Invalid PAN number. Format: AAAAA9999A")
    return v.upper()

  @field_validator("gst_no")
  def validate_gst_no(cls, v):
    regex = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    if not re.fullmatch(regex, v.upper()):
      raise ValueError("Invalid GST number. Please check the format.")
    return v.upper()

class UpdateCompany(BaseModel):
  name: str
  about: str
  category_id: str
  subcategory_id: int
  active_status: int
  address: str
  phone_number: str
  email: EmailStr
  pan_no: str = Field(..., description="PAN number")
  gst_no: str = Field(..., description="GST number")
  website: str = Field(..., description="Website")
  logo_url: Optional[str] = None

  @field_validator("phone_number")
  @classmethod
  def validate_phone_number(cls, v):
    regex = r"^[6789]\d{9}$"
    if not re.fullmatch(regex, v):
      raise ValueError(
        "Invalid Indian phone number. Must be 10 digits starting with 6-9."
      )
    return v

  @field_validator("pan_no")
  @classmethod
  def validate_pan_no(cls, v):
    regex = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    if not re.fullmatch(regex, v.upper()):
      raise ValueError("Invalid PAN number. Format: AAAAA9999A")
    return v.upper()

  @field_validator("gst_no")
  @classmethod
  def validate_gst_no(cls, v):
    regex = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    if not re.fullmatch(regex, v.upper()):
      raise ValueError("Invalid GST number. Please check the format.")
    return v.upper()

  @classmethod
  def as_form(
    cls,
    name: str = Form(...),
    about: str = Form(...),
    category_id: str = Form(...),
    subcategory_id: int = Form(...),
    active_status: int = Form(...),
    address: str = Form(...),
    phone_number: str = Form(...),
    email: EmailStr = Form(...),
    pan_no: str = Form(...),
    gst_no: str = Form(...),
    website: str = Form(...),
    logo_url: Optional[str] = Form(None)
  ):
    return cls(
      name=name,
      about=about,
      category_id=category_id,
      subcategory_id=subcategory_id,
      active_status=active_status,
      address=address,
      phone_number=phone_number,
      email=email,
      pan_no=pan_no,
      gst_no=gst_no,
      website=website,
      logo_url=logo_url
    )
  
class AddAgent(BaseModel):
  company_id: str
  name: str
  email: EmailStr
  phone_number: str
  address: str
  pincode: str
  state: str
  since: Optional[str] = None  
  nationality: str
  listing: Optional[str] = None  
  review: str
  

  @field_validator("phone_number")
  def validate_phone_number(cls, v):
    regex = r"^[6789]\d{9}$"
    if not re.fullmatch(regex, v):
      raise ValueError(
        "Invalid Indian phone number. Must be 10 digits starting with 6-9."
      )
    return v
    
class UpdateAgent(BaseModel):
  name: Optional[str] = None
  email: Optional[EmailStr] = None
  phone_number: Optional[str] = None
  address: Optional[str] = None
  pincode: Optional[str] = None
  state: Optional[str] = None

  @field_validator("phone_number")
  def validate_phone(cls, v):
    if v:
      regex = r"^[6789]\d{9}$"
      if not re.fullmatch(regex, v):
        raise ValueError("Invalid Indian phone number")
    return v

class AddClient(BaseModel):
  name: str 
  address: str
  city: str 
  state: str 
  pincode: str 
  country : str
  phone_number: str 
  email: EmailStr 

  @field_validator("phone_number")
  def validate_phone_number(cls, v):
    regex = r"^[6789]\d{9}$"
    if not re.fullmatch(regex, v):
      raise ValueError(
        "Invalid Indian phone number. Must be 10 digits starting with 6-9."
      )
    return v

class UpdateClient(BaseModel):
  name: Optional[str] = None
  address: Optional[str] = None
  city: Optional[str] = None
  state: Optional[str] = None
  pincode: Optional[str] = None
  country: Optional[str] = None 
  phone_number: Optional[str] = None
  email: Optional[EmailStr] = None

  @field_validator("phone_number")
  def validate_phone_number(cls, v):
    regex = r"^[6789]\d{9}$"
    if not re.fullmatch(regex, v):
      raise ValueError(
        "Invalid Indian phone number. Must be 10 digits starting with 6-9."
      )
    return v

