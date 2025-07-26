import time
import hmac
import base64
import hashlib
from typing import Optional
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.utilities.convert_object_id import objid
from config import CAPTCHA_SECRET_KEY,JWT_SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.database.db import user_collection
from email.message import EmailMessage
from bson import ObjectId
import string,os,random
from datetime import datetime
from app.database.db import car_collection
from pymongo import ASCENDING, DESCENDING

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def generate_captcha_text(length=5):
    base36 = ''.join(filter(str.isalnum, uuid.uuid4().hex.upper()))
    return base36[:length]

def generate_captcha_token(ip: str, captcha_text: str) -> str:
    timestamp = str(int(time.time()))
    message = f"{ip}:{timestamp}:{captcha_text}"
    signature = hmac.new(CAPTCHA_SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(f"{timestamp}:{captcha_text}:{signature.hex()}".encode()).decode()


def verify_captcha_token(token: str, user_input: str, ip: str, max_age=300) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        timestamp_str, captcha_text, signature = decoded.split(":")
        timestamp = int(timestamp_str)
        if time.time() - timestamp > max_age:
            return False  # expired

        expected_message = f"{ip}:{timestamp_str}:{captcha_text}"
        expected_signature = hmac.new(
            CAPTCHA_SECRET_KEY.encode(), expected_message.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            return False

        return captcha_text.upper() == user_input.upper()

    except Exception as e:
        return False

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")

        if not user_id or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID or role",
            )

        user = user_collection.find_one({"_id": objid(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"],
            "role": role
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

# Optional JWT decoding function
def decode_jwt_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None
    
#generate random password
def generate_random_password(limit=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=limit))   

#convert object id
def get(doc):
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, datetime):
            doc[key] = value.isoformat()
        elif isinstance(value, dict):
            doc[key] = get(value)
        elif isinstance(value, list):
            doc[key] = [get(item) if isinstance(item, dict) else item for item in value]
    return doc

def get_next_row_number():
    # Find the last document having meta_data.row_number and sort descending
    last_doc = car_collection.find(
        {"meta_data.row_number": {"$exists": True}}
    ).sort("meta_data.row_number", -1).limit(1)

    doc_list = list(last_doc)
    if doc_list:
        last_row_number = doc_list[0]["meta_data"]["row_number"]
        return last_row_number + 1

    # No cars in the collection with row_number
    return 1
