# import base64
# import hashlib
# import hmac
# import secrets
# import time
# import uuid
# from config import CAPTCHA_SECRET_KEY

# captcha_secret_key = secrets.token_urlsafe(32)
# print(captcha_secret_key)


# def generate_captcha_text(length=5):
#     base36 = "".join(filter(str.isalnum, uuid.uuid4().hex.upper()))
#     return base36[:length]


# captcha_text = generate_captcha_text()
# print(captcha_text)


# # Only for captcha token generate.
# def generate_captcha_token(ip: str) -> str:
#     timestamp = str(int(time.time()))
#     message = f"{ip}:{timestamp}"
#     signature = hmac.new(
#         CAPTCHA_SECRET_KEY.encode(), message.encode(), hashlib.sha256
#     ).digest()
#     return base64.urlsafe_b64encode(f"{timestamp}:{signature.hex()}".encode()).decode()


# # Only for create company deatils
# @motorapi_router.post("/add-company")
# async def add_company(RequestBody: AddCompany):
#     try:
#         existing_company = company_collection.find_one({"name": RequestBody.name})
#         if existing_company:
#             raise HTTPException(status_code=400, detail="Company name already exists")

#         category = category_collection.find_one({"_id": objid(RequestBody.category_id)})
#         if not category:
#             raise HTTPException(status_code=404, detail="Category not found")

#         subcat_ids = [sub["id"] for sub in category.get("subcategories", [])]
#         if RequestBody.subcategory_id not in subcat_ids:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Subcategory ID not valid for the given category",
#             )

#         data = {
#             "name": RequestBody.name,
#             "status": RequestBody.status,
#             "about": RequestBody.about,
#             "category_id": objid(RequestBody.category_id),
#             "subcategory_id": RequestBody.subcategory_id,
#             "created_at": datetime.datetime.utcnow(),
#         }

#         insert_data = company_collection.insert_one(data)
#         response_data = company_collection.find_one({"_id": insert_data.inserted_id})
#         response_data["_id"] = str(response_data["_id"])
#         response_data["category_id"] = str(response_data["category_id"])

#         return {"message": "Company added successfully", "data": response_data}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @motorapi_router.post("/upload-company-files/{company_id}")
# async def upload_company_files(
#     company_id: str,
#     logo: UploadFile = File(...),
#     photo: UploadFile = File(...),
#     request: Request = None,
# ):
#     try:
#         company = company_collection.find_one({"_id": objid(company_id)})
#         if not company:
#             raise HTTPException(status_code=404, detail="Company not found")

#         # Save logo
#         logo_ext = logo.filename.split(".")[-1]
#         logo_filename = f"{company_id}_logo.{logo_ext}"
#         logo_path = f"static/logos/{logo_filename}"
#         with open(logo_path, "wb") as buffer:
#             shutil.copyfileobj(logo.file, buffer)
#         logo_url = f"{request.base_url}static/logos/{logo_filename}"

#         # Save photo
#         photo_ext = photo.filename.split(".")[-1]
#         photo_filename = f"{company_id}_photo.{photo_ext}"
#         photo_path = f"static/photos/{photo_filename}"
#         with open(photo_path, "wb") as buffer:
#             shutil.copyfileobj(photo.file, buffer)
#         photo_url = f"{request.base_url}static/photos/{photo_filename}"

#         # Update DB
#         company_collection.update_one(
#             {"_id": objid(company_id)},
#             {"$set": {"logo_path": logo_url, "photo_path": photo_url}},
#         )

#         return {
#             "message": "Files uploaded successfully",
#             "logo_url": logo_url,
#             "photo_url": photo_url,
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# # Upload photos
# @motorapi_router.post("/upload-photos")
# async def upload_photos(
#     photos: List[UploadFile] = File(...),
#     request: Request = None,
# ):
#     try:
#         uploaded_photo_urls = []

#         for photo in photos:
#             extension = photo.filename.split(".")[-1]
#             filename = f"{uuid.uuid4().hex}.{extension}"
#             file_path = f"static/photo/{filename}"

#             with open(file_path, "wb") as buffer:
#                 shutil.copyfileobj(photo.file, buffer)

#             photo_url = f"{request.base_url}static/photo/{filename}"
#             uploaded_photo_urls.append(photo_url)

#         return {
#             "message": "Photos uploaded successfully",
#             "photo_urls": uploaded_photo_urls,
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @motorapi_router.get("/get-photos")
# async def get_photos(request: Request):
#     try:
#         photo_dir = "static/photo"
#         if not os.path.exists(photo_dir):
#             raise HTTPException(status_code=404, detail="Photo directory not found")

#         photo_files = [
#             f"{request.base_url}static/photo/{filename}"
#             for filename in os.listdir(photo_dir)
#             if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
#         ]

#         return {"message": "Photo URLs fetched successfully", "photos": photo_files}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# # @motorapi_router.post("/upload-photo")
# # async def upload_photo(
# #     company_id: str, photo: UploadFile = File(...), request: Request = None
# # ):
# #     try:
# #         company = company_collection.find_one({"_id": objid(company_id)})
# #         if not company:
# #             raise HTTPException(status_code=404, detail="Company not found")

# #         file_ext = photo.filename.split(".")[-1]
# #         filename = f"{company_id}_logo.{file_ext}"
# #         file_path = f"static/logos/{filename}"

# #         with open(file_path, "wb") as buffer:
# #             shutil.copyfileobj(photo.file, buffer)

# #         logo_url = f"{request.base_url}static/logos/{filename}"
# #         company_collection.update_one(
# #             {"_id": objid(company_id)}, {"$set": {"logo_path": logo_url}}
# #         )

# #         return {"message": "Logo uploaded successfully", "logo_path": logo_url}

# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=str(e))



from datetime import datetime, timedelta, timezone
from jose import jwt

JWT_SECRET_KEY = "a20bb1d0fba2242b30948bd77e4d16cc90e7f00b29aa1df6060d279b90fe0359"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

# Example usage
v = create_access_token({"sub": "johndoe"})
print(v)
