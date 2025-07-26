from fastapi import Form, Depends
from pydantic import EmailStr
from typing import List, Optional

from app.models.admin.admin import AddCompany

def get_company_form(
    name: str = Form(...),
    about: str = Form(...),
    category_id: str = Form(...),
    subcategory_id: int = Form(...),
    active_status: int = Form(...),
    address: str = Form(...),
    phone_number: str = Form(...),
    email: EmailStr = Form(...),
    currency: str = Form(...),
    pan_no: str = Form(...),
    gst_no: str = Form(...),
    website: str = Form(...),
    logo_url: Optional[str] = Form(None)
):
    return AddCompany(
        name=name,
        about=about,
        category_id=category_id,
        subcategory_id=subcategory_id,
        active_status=active_status,
        address=address,
        phone_number=phone_number,
        email=email,
        currency=currency,
        pan_no=pan_no,
        gst_no=gst_no,
        website=website,
        logo_url=logo_url
    )
