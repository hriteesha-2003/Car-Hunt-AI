import os
import shutil
from typing import List, Optional
import uuid,boto3
from uuid import uuid4
from pydantic import EmailStr
from bson import ObjectId
from io import BytesIO
from botocore.exceptions import NoCredentialsError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.database.connections import connect
from app.models.admin.admin import AddAgent, AddClient, AddCompany, UpdateAgent, UpdateClient, UpdateCompany
from app.schemas.schema import get_company_form
from app.models.about_us.about import AboutUsSchema
from app.utilities.convert_object_id import convert_object_ids, objid
from app.utilities.helper import refresh_agent_listing
from app.utilities.security import get_current_user,get
from config import DATABASE_NAME, CATEGORY_COLLECTION,ALLOWED_EXTENSIONS, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_BUCKET_URL,PRIVACY_COLLECTION_NAME, ABOUT_US_COLLECTION, BOTTOM_SLIDER_COLLECTION,SETTINGS_COLLECTION, FAQ_COLLECTION, USER_COLLECTION
from app.database.db import db, car_collection,category_collection, company_collection, client_collection,agent_collection,videos_collection,photos_collection,messages_collection,ai_agent_collection,home_featured_items,privacy_collection,about_us_collection,bottom_slider_collection,settings_collection,faq_collection,user_collection
from datetime import datetime, timezone
from datetime import date
from app.models.type.type import FAQType
from app.models.settings.settings import AppLinks,VideoLinks,SocialLinks,SettingsSchema
from app.models.privacy.privacy import PrivacyPolicy
from app.models.message.message import MessageOut
from app.models.AI_Agent.AIagent import AddAIAgent, AIAgentResponse
from app.models.home_featured_items.home import HomeFeaturedItems,UpdateHomeFeaturedItem
from app.services.message import get_chat_history, mark_as_read
from app.services.email_service import EmailService
from app.utilities.security import create_access_token, hash_password, verify_password,generate_random_password
from app.services.S3 import upload_to_s3
from app.services.json import return_error_json, return_json
import traceback
motorapi_router = APIRouter(
    prefix="/admin/motor-api",
    tags=["motorAPI"],
)

# Add company 
@motorapi_router.post("/add-company")
async def add_company(
    request_body: AddCompany = Depends(get_company_form),  
    logo: Optional[UploadFile] = File(None),
    request: Request = None,
    current_user: dict = Depends(get_current_user),
):
    try:
        # Check if company name already exists
        if company_collection.find_one({"name": request_body.name}):
            raise HTTPException(status_code=400, detail="Company name already exists")
        new_password = generate_random_password()
        hashed_password = hash_password(new_password)
        print(new_password)

        # Auto-determine status
        role = current_user.get("role")
        company_status = "approved" if role in ["admin", "superuser"] else "pending"
        company_data = request_body.model_dump()
        company_data.update({
            "status": company_status,
            "created_by": current_user["username"],
            "user_email": current_user["email"],
            "created_at": datetime.now(timezone.utc),
            "password": hashed_password
        })
          
        if logo:
            filename = f"{uuid4().hex}.{logo.filename.split('.')[-1]}"
            logo_url = upload_to_s3(file=logo, filename=filename)  
                       
            company_data["logo_url"] = logo_url
            
        insert_result = company_collection.insert_one(company_data)

        # Send email to company email
        user_data = {
            "role": "admin",
            "username": request_body.email,
            "email": request_body.email,
            "password": hashed_password,
            "is_superuser": False,
            "created_at": datetime.now(timezone.utc)
        }
        user_collection.insert_one(user_data)

          # Send email with login credentials
        email_service = EmailService(db)
        try:email_service.send_email( template_type="password", to_email=request_body.email, password=new_password,
    username=request_body.name
)

        except Exception as email_error:
            raise HTTPException(
                status_code=500,
                detail=f"Company created but email sending failed: {email_error}"
            )
        
        response_data = company_collection.find_one({"_id": insert_result.inserted_id})
        response_data["_id"] = str(response_data["_id"])
        
        response_data["created_at"] = response_data["created_at"].isoformat()

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Company added successfully", "data": response_data}
        )
    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
# Get company using company id
@motorapi_router.get("/get-company/{company_id}")
async def get_company(
    company_id: str, 
    request: Request, 
    
):
    try:
       
        company = company_collection.find_one({"_id": objid(company_id)})
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        company_id_str = str(company["_id"])
      
        
        agent_count = agent_collection.count_documents({"company_id": company_id_str})

       
        active_listing = car_collection.count_documents({
            "company_id": company_id_str,
            "status": {"$regex": "^approved$", "$options": "i"}
        })

        # ✅ Build response data
        company_data = {
            "_id": company_id_str,
            "name": company.get("name"),
            "about": company.get("about"),
            "active_status": company.get("active_status"),
            "address": company.get("address"),
            "phone_number": company.get("phone_number"),
            "email": company.get("email"),
            "pan_no": company.get("pan_no"),
            "gst_no": company.get("gst_no"),
            "website": company.get("website"),
            "status": company.get("status"),
            "created_by": company.get("created_by"),
            "created_at": company.get("created_at").isoformat() if company.get("created_at") else None,
            "logo_url": company.get("logo_url"),
            "agent_count": agent_count,
            "active_listing": active_listing
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": company_data}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all companies
@motorapi_router.get("/get-all-companies")
async def get_all_companies(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    try:
        query = {"is_deleted": {"$ne": True}}
        skip = (page - 1) * limit

    
        companies_cursor = company_collection.find(query).skip(skip).limit(limit)
        companies = []

        for company in companies_cursor:  
            company_id = company["_id"]
            company_id_str = str(company_id)

            
            agent_count = agent_collection.count_documents({"company_id": company_id_str})
            active_listing = car_collection.count_documents({
                "company_id": company_id_str,
                "status": "approved"
            })

            
            companies.append({
                "_id": company_id_str,
                "name": company.get("name"),
                "about": company.get("about"),
                "active_status": company.get("active_status"),
                "address": company.get("address"),
                "phone_number": company.get("phone_number"),
                "email": company.get("email"),
                "pan_no": company.get("pan_no"),
                "gst_no": company.get("gst_no"),
                "website": company.get("website"),
                "status": company.get("status"),
                "created_by": company.get("created_by"),
                "created_at": company.get("created_at").isoformat() if company.get("created_at") else None,
                "logo_url": company.get("logo_url"),

                
                "agent_count": agent_count,
                "active_listing": active_listing
            })
            active_car_count_debug = list(car_collection.find({"company_id": company_id_str}))
            
            active_listing_debug = list(car_collection.find({"company_id": company_id_str, "status": "approved"}))
           


        total_count = company_collection.count_documents(query)
        total_pages = (total_count + limit - 1) // limit

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "data": companies,
                "page_info": {
                    "page": page,
                    "limit": limit,
                    "total_records": total_count,
                    "total_pages": total_pages
                }
            }
        )

    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# Update company using company id (change all fields)
@motorapi_router.put("/update-company/{company_id}")
async def update_company(
    company_id: str,
    request_body: UpdateCompany = Depends(UpdateCompany.as_form),
    company_status: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        company = company_collection.find_one({"_id": objid(company_id)})
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Role-based access
        role = current_user["role"]
        is_admin = role in ["admin", "superuser"]
        if not is_admin and company.get("created_by") != current_user["username"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this company")

        # Validate company_status
        allowed_statuses = {"approved", "rejected", "pending", "draft"}
        if company_status and is_admin and company_status not in allowed_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid company_status: {company_status}")

        final_status = (
            company_status if is_admin and company_status
            else company.get("status", "approved") if is_admin
            else "pending"
        )

        # Build update dict
        raw_data = request_body.model_dump(exclude_unset=True)
        company_data = {k: v for k, v in raw_data.items() if v is not None}

        # Add audit info
        company_data.update({
            "status": final_status,
            "updated_by": current_user["username"],
            "updated_at": datetime.now(timezone.utc),
        })

        # Handle logo upload
        if logo and logo.filename:
            file_ext = logo.filename.split(".")[-1]
            company_name_safe = company["name"].replace(" ", "_").lower()
            filename = f"{company_id}_logo.{file_ext}"
            
            logo_url = upload_to_s3(logo, filename)
            company_data["logo_url"] = logo_url
            print(f"Logo uploaded. S3 URL: {logo_url}")

        # No valid data to update
        if not company_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Update in DB
        result = company_collection.update_one(
            {"_id": objid(company_id)},
            {"$set": company_data}
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Company updated successfully"}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Upload photos for a company usign company id
# @motorapi_router.post("/upload-photos/{company_id}")
# async def upload_photos(
#     company_id: str,
#     photos: List[UploadFile] = File(...),
#     request: Request = None, current_user: dict = Depends(get_current_user)
# ):
#     try:

#         if current_user["role"] not in ["admin", "superuser"]:
#             raise HTTPException(status_code=403, detail="You are not authorized to upload company photos.")
        
#         company = company_collection.find_one({"_id": objid(company_id)})
#         if not company:
#             raise HTTPException(status_code=404, detail="Company not found")
        
#         # Prepare directory for saving photos
#         company_name = company["name"].replace(" ", "_").lower()
#         company_dir = f"https://motorfinder.s3.eu-north-1.amazonaws.com/photo/{company_name}"
#         os.makedirs(company_dir, exist_ok=True)

#         uploaded_photo_urls = []
#         bucket_name = "motorfinderuae"

#         for photo in photos:
#             extension = photo.filename.split(".")[-1]
#             filename = f"{uuid.uuid4().hex}.{extension}"
#             file_path = os.path.join(company_dir, filename)
#             s3_key = f"photo/{company_name}/{filename}"
            

#             try:
#                 s3.upload_fileobj(photo.file, bucket_name, s3_key)
#                 photo_url = f"https://{bucket_name}.s3.eu-north-1.amazonaws.com/{s3_key}"
#                 uploaded_photo_urls.append(photo_url)

#                 print(photos_collection,"<--------PHOTO COLLCTION")
#                 inert_respose = photos_collection.insert_one({
#                     "company_id": company["_id"],
#                     "photo_url": photo_url,
#                     "uploaded_at": datetime.utcnow()
#                 })
#                 print(inert_respose)
#             except NoCredentialsError:
#               raise HTTPException(status_code=500, detail="AWS credentials not found.")
#             except Exception as e:
#                  raise HTTPException(status_code=500, detail=f"S3 Upload failed: {str(e)}")
    
            

            
#             photo_url = f"https://motorfinder.s3.eu-north-1.amazonaws.com/photo/{company_name}/{filename}"
#             uploaded_photo_urls.append(photo_url)

#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={"message": "Photos uploaded successfully", "photo_urls": uploaded_photo_urls}
#         )

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
# Get photos for a company using company id
@motorapi_router.get("/get-photos/{company_id}")
async def get_photos(company_id: str, request: Request):
    try:
        company = db[os.getenv("COMPANY_COLLECTION")].find_one({"_id": objid(company_id)})
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        photos_cursor = photos_collection.find(
            {"company_id": company["_id"]},
            {"_id": 0, "photo_url": 1, "uploaded_at": 1}
        ).sort("uploaded_at", -1)

        all_photos = []
        for photo in photos_cursor:
            if "uploaded_at" in photo and isinstance(photo["uploaded_at"], datetime):
                photo["uploaded_at"] = photo["uploaded_at"].isoformat()
            all_photos.append(photo)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Photos fetched successfully",
                "photos": all_photos,
                "company_id": str(company["_id"]),
                "company_name": company["name"]
            }
        )
     
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    

   

# Upload video for a company
@motorapi_router.post("/upload-video/{company_id}")
async def upload_video(
    company_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    videos: Optional[List[UploadFile]] = File(default=[]),
    video_urls: Optional[List[str]] = Form(default=[]),
):
    try:
        if current_user["role"] not in ["admin", "superuser"]:
            raise HTTPException(403, "You are not authorized to upload company videos.")

        company = company_collection.find_one({"_id": objid(company_id)})
        if not company:
            raise HTTPException(404, "Company not found")

        if not videos and not video_urls:
            raise HTTPException(400, detail="Send at least one file or one video URL.")

        company_name = company["name"].replace(" ", "_").lower()
        saved_entries = []
        bucket_name = "motorfinderuae"


        for video in videos:
            ext = video.filename.split(".")[-1].lower()
            if ext not in {"mp4", "mov", "avi", "webm"}:
                continue  

            filename = f"{uuid.uuid4().hex}.{ext}"
            

            try:
                
                video_url = upload_to_s3(video, filename)

                # FIX HERE: Insert video metadata in MongoDB
                videos_collection.insert_one({
                    "company_id": company["_id"],
                    "company_name": company["name"],
                    "video_url": video_url,
                    "original_filename": video.filename,
                    "source": "upload",
                    "uploaded_by": current_user.get("_id"),
                    "uploaded_at": datetime.utcnow(),
                })
                saved_entries.append(video_url)

            except Exception as e:
                raise HTTPException(500, detail=f"Video upload failed: {str(e)}")  # FIX HERE: Proper error handling


        for url in video_urls:
            url = url.strip()
            if url:
                videos_collection.insert_one({
                    "company_id": company["_id"],
                    "company_name": company["name"],
                    "video_url": url,
                    "original_filename": None,
                    "source": "url",
                    "uploaded_by": current_user.get("_id"),
                    "uploaded_at": datetime.utcnow(),
                })
                saved_entries.append(url)

        all_videos_cursor = videos_collection.find(
            {"company_id": company["_id"]},
            {"_id": 0, "video_url": 1, "source": 1, "uploaded_at": 1}
        ).sort("uploaded_at", -1)

        all_videos = []
        for vid in all_videos_cursor:
            if "uploaded_at" in vid and isinstance(vid["uploaded_at"], datetime):
                vid["uploaded_at"] = vid["uploaded_at"].isoformat()
            all_videos.append(vid)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Videos saved successfully",
                "newly_uploaded": saved_entries,
                "all_videos": all_videos,
                "company_id": str(company["_id"]),
                "company_name": company["name"],
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, detail=str(exc))

# Get all videos for a company
@motorapi_router.get("/get-all-videos/{company_id}")
async def get_all_videos(
    company_id: str,
    request: Request,
):
    try:
        company = company_collection.find_one({"_id": objid(company_id)})
        if not company:
            raise HTTPException(404, "Company not found")

        all_videos_cursor = videos_collection.find(
            {"company_id": company["_id"]},
            {"_id": 0, "video_url": 1, "source": 1, "uploaded_at": 1}
        ).sort("uploaded_at", -1)

        all_videos = []
        for vid in all_videos_cursor:
            if "uploaded_at" in vid and isinstance(vid["uploaded_at"], datetime):
                vid["uploaded_at"] = vid["uploaded_at"].isoformat()
            all_videos.append(vid)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Videos saved successfully",
                "all_videos": all_videos,
                "company_id": str(company["_id"]),
                "company_name": company["name"],
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, detail=str(exc))
    
# Approve company 
@motorapi_router.post("/approve-company/{company_id}")
async def approve_company(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to approve companies.")

        result = company_collection.update_one(
            {"_id": objid(company_id), "status": "pending"},
            {
                "$set": {
                    "status": "approved",
                    "updated_by": current_user["username"],
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="No pending company found to approve.")

        updated_company = company_collection.find_one({"_id": objid(company_id)})
        updated_company = convert_object_ids(updated_company)
        encoded_company = jsonable_encoder(updated_company)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Company approved successfully", "data": encoded_company}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Reject company by admin
@motorapi_router.post("/reject-company/{company_id}")
async def reject_company(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to approve companies.")

        result = company_collection.update_one(
            {"_id": objid(company_id), "status": "pending"},
            {
                "$set": {
                    "status": "rejected",
                    "updated_by": current_user["username"],
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="No pending company found to reject.")

        updated_company = company_collection.find_one({"_id": objid(company_id)})
        updated_company = convert_object_ids(updated_company)
        encoded_company = jsonable_encoder(updated_company)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Company rejected successfully", "data": encoded_company}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Soft delete company
@motorapi_router.delete("/delete-company/{company_id}")
async def delete_company(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to delete companies.")

        result = company_collection.update_one(
            {"_id": objid(company_id), "is_deleted": {"$ne": True}},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Company not found or already deleted")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Company soft deleted successfully"}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Restore company
@motorapi_router.post("/restore-company/{company_id}")
async def restore_company(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to restore companies.")

        result = company_collection.update_one(
            {"_id": objid(company_id), "is_deleted": True},
            {"$set": {"is_deleted": False, "restored_at": datetime.now(timezone.utc)}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Company not found or not deleted")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Company restored successfully"}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add agent
@motorapi_router.post("/add-agent")
async def add_agent(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    date_of_birth: date = Form(...),
    position: str = Form(...),
    company_id: str = Form(...),
    phone_number: str = Form(...),
    address: str = Form(...),
    # Optional fields
    full_name: Optional[str] = Form(None),
    date_of_joining: Optional[date] = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    request: Request = None,
    nationality: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Check company exists
        company = company_collection.find_one({"_id": objid(company_id)})
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Check agent email uniqueness
        if agent_collection.find_one({"email": email}):
            raise HTTPException(status_code=400, detail="Agent with this email already exists")
        profile_picture_url= None

        
        if profile_picture:
            filename = f"{uuid.uuid4()}_{profile_picture.filename}"
            
            profile_picture_url = upload_to_s3(profile_picture, filename)
            
        created_time = datetime.now(timezone.utc)
        agent_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "date_of_birth": date_of_birth.isoformat(),
            "position": position,
            "company_id": convert_object_ids(company_id),
            "company_name": company.get("name", "Unknown"),
            "logo": company.get("logo_url", "Unknown"),
            "status": "pending",
            "created_by": current_user["username"],
            "role": "agent",
            "created_at": created_time.isoformat(),
            # "since": created_time.strftime("%Y-%m-%d"),
            "date_of_joining": date_of_joining.isoformat() if date_of_joining else "",
            "listing": "0",
            "profile_picture_url": profile_picture_url,
            "phone_number": phone_number,
            "full_name": full_name,
            "address": address,
            "nationality": nationality,
            "description": description
        }

        # Insert into DB
        insert_result = agent_collection.insert_one(agent_data)
        inserted_id = insert_result.inserted_id

        # Update listing count
        refresh_agent_listing(inserted_id)

        # Return response
        response_data = agent_collection.find_one({"_id": inserted_id})
        response_data["_id"] = str(response_data["_id"])

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Agent added successfully", "data": response_data}
        )

    except HTTPException as e:
        print(e)
        raise e
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))



@motorapi_router.get("/get-agent/{agent_id}")
async def get_agent(agent_id: str):
    try:
        agent = agent_collection.find_one({"_id": objid(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Convert ObjectId
        agent["_id"] = str(agent["_id"])

        # Print/log types to debug
        print("created_at:", agent.get("created_at"), type(agent.get("created_at")))
        print("updated_at:", agent.get("updated_at"), type(agent.get("updated_at")))

        # Convert only if it's a datetime
        if "created_at" in agent and isinstance(agent["created_at"], datetime):
            agent["created_at"] = agent["created_at"].isoformat()

        if "updated_at" in agent and isinstance(agent["updated_at"], datetime):
            agent["updated_at"] = agent["updated_at"].isoformat()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": agent}
        )

    except HTTPException as e:
        raise e 

    except Exception as e:
        # Better visibility of error
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# Get all agents
@motorapi_router.get("/get-all-agents")
async def get_agents(
    # current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    company_id: Optional[str] = Query(None)
):

    try:
        # role = current_user.get("role")
        skip = (page - 1) * limit

        # Base filter to exclude soft-deleted agents
        query = {"is_deleted": {"$ne": True}}
        if company_id:
            query["company_id"] = {"$in": [str(company_id)]}

        total_count = agent_collection.count_documents(query)
        total_pages = (total_count + limit - 1) // limit

        agents_cursor = agent_collection.find(query).skip(skip).limit(limit)
        agents = [jsonable_encoder({**agent, "_id": str(agent["_id"])}) for agent in agents_cursor]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "List of agents",
                "data": agents,
                "page_info": {
                    "page": page,
                    "limit": limit,
                    "total_records": total_count,
                    "total_pages": total_pages
                }
            }
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update agent using agent id 
@motorapi_router.put("/update-agent/{agent_id}")
async def update_agent(
    agent_id: str,
    first_name: Optional[str] = Form(...),
    last_name: Optional[str] = Form(...),
    email: Optional[EmailStr] = Form(None),
    phone_number: Optional[str] = Form(None),
    pincode: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    logo: Optional[List[UploadFile]] = File(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Step 1: Find the agent
        agent = agent_collection.find_one({"_id": objid(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Step 2: Find the associated company
        company = company_collection.find_one({"_id": objid(agent["company_id"])})
        if not company:
            raise HTTPException(status_code=404, detail="Associated company not found")

        # Step 3: Check permissions
        role = current_user.get("role")
        is_admin_or_superuser = role in ["admin", "superuser"]
        is_company_creator = company.get("created_by") == current_user["username"]

        if not (is_admin_or_superuser or is_company_creator):
            raise HTTPException(status_code=403, detail="Not authorized to update this agent")

        # Step 4: Prepare update data
        updated_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone_number": phone_number,
            "pincode": pincode,
            "state": state,
            "address": address,
        }

        # Step 5: Handle logo upload
        if logo:
            file = logo[0]
            uploaded_logo_url = upload_to_s3(file,file.filename)
            updated_data["logo"] = uploaded_logo_url

        # Step 6: Remove fields with None
        updated_data = {k: v for k, v in updated_data.items() if v is not None}

        if not updated_data:
            raise HTTPException(status_code=400, detail="No valid fields provided to update")

        updated_data["updated_at"] = datetime.now(timezone.utc)

        # Step 7: Update in DB
        agent_collection.update_one(
            {"_id": objid(agent_id)}, {"$set": updated_data}
        )

        # Step 8: Fetch and return updated agent
        updated_agent = agent_collection.find_one({"_id": objid(agent_id)})
        updated_agent["_id"] = str(updated_agent["_id"])
        updated_agent = jsonable_encoder(updated_agent)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Agent updated successfully", "data": updated_agent}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Approve agent using agent id 
@motorapi_router.post("/approve-agent/{agent_id}")
async def approve_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to approve agent.")
        
        # Update the agent's status
        result = agent_collection.update_one(
            {"_id": objid(agent_id), "status": "pending"},
            {"$set": {
                "status": "approved",
                "updated_by": current_user["username"],
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Pending agent not found")

        # Fetch updated agent
        updated_agent = agent_collection.find_one({"_id": objid(agent_id)})
        updated_agent["_id"] = str(updated_agent["_id"])
        updated_agent = jsonable_encoder(updated_agent)

        return JSONResponse(
            status_code=status.HTTP_200_OK, 
            content = {"message": "Agent approved successfully", "data": updated_agent}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Reject agent using agent id   
@motorapi_router.post("/reject-agent/{agent_id}")
async def reject_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to approve agent.")
        
        # Update the agent's status
        result = agent_collection.update_one(
            {"_id": objid(agent_id), "status": "pending"},
            {"$set": {
                "status": "rejected",
                "updated_by": current_user["username"],
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Pending agent not found")

        # Fetch updated agent
        updated_agent = agent_collection.find_one({"_id": objid(agent_id)})
        updated_agent["_id"] = str(updated_agent["_id"])
        updated_agent = jsonable_encoder(updated_agent)

        return JSONResponse(
            status_code=status.HTTP_200_OK, 
            content = {"message": "Agent rejected successfully", "data": updated_agent}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Delete agent
@motorapi_router.delete("/delete-agent/{agent_id}")
async def delete_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="Unauthorized role")

        agent = agent_collection.find_one({"_id": objid(agent_id), "is_deleted": {"$ne": True}})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found or already deleted")

        agent_collection.update_one(
            {"_id": objid(agent_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Agent deleted successfully"}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Restore agent
@motorapi_router.post("/restore-agent/{agent_id}")
async def restore_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="Unauthorized role")

        agent = agent_collection.find_one({"_id": objid(agent_id), "is_deleted": True})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found or not deleted")

        agent_collection.update_one(
            {"_id": objid(agent_id)},
            {"$set": {"is_deleted": False, "restored_at": datetime.now(timezone.utc)}}
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Agent restored successfully"}
        )
    except HTTPException as e:
        raise e




# Add client
@motorapi_router.post("/add-client")
async def add_client(request_body: AddClient, request: Request):
    try:
        # Fields to check for duplicates
        duplicate_checks = {
            "phone_number": request_body.phone_number,
            "email": request_body.email,
        }

        # Perform duplicate checks
        for field, value in duplicate_checks.items():
            if client_collection.find_one({field: value}):
                raise HTTPException(
                    status_code=400,
                    detail=f"Client with this {field.replace('_', ' ')} already exists",
                )

        # Insert new client
        client_data = request_body.model_dump()
        client_data["created_at"] = datetime.now(timezone.utc).isoformat()
        insert_result = client_collection.insert_one(client_data)
        inserted_id = insert_result.inserted_id

        # Fetch and return the inserted client
        response_data = client_collection.find_one({"_id": inserted_id})
        response_data["_id"] = str(response_data["_id"])

        return JSONResponse(
            status_code=status.HTTP_201_CREATED, 
            content={"message": "Client added successfully", "data": response_data}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get client using client id
@motorapi_router.get("/get-client/{client_id}")
async def get_client(client_id: str, request: Request):
    try:
        client = client_collection.find_one({"_id": objid(client_id)})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        client["_id"] = str(client["_id"])

        return JSONResponse(
            status_code=status.HTTP_200_OK, 
            content = {"data": client}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all clients
@motorapi_router.get("/get-all-clients")
async def get_all_clients(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        role = current_user.get("role")

        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        skip = (page - 1) * limit

        query = {"is_deleted": {"$ne": True}}

        total_count = client_collection.count_documents(query)
        total_pages = (total_count + limit - 1) // limit

        clients_cursor = client_collection.find(query).skip(skip).limit(limit)

        clients = []
        for client in clients_cursor:
            client["_id"] = str(client["_id"])
            clients.append(jsonable_encoder(client))

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "List of all clients",
                "data": clients,
                "page_info": {
                    "page": page,
                    "limit": limit,
                    "total_records": total_count,
                    "total_pages": total_pages
                }
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update client
@motorapi_router.put("/update-client/{client_id}")
async def update_client(request_body: UpdateClient, client_id: str):
    try:
        client = client_collection.find_one({"_id": objid(client_id)})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Prepare updated data
        updated_data = request_body.model_dump()
        updated_data["updated_at"] = datetime.utcnow()

        # Update the client in DB
        update_result = client_collection.update_one(
            {"_id": objid(client_id)}, {"$set": updated_data}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to the client")

        updated_client = client_collection.find_one({"_id": objid(client_id)})
        updated_client["_id"] = str(updated_client["_id"])
        updated_client = jsonable_encoder(updated_client)

        return JSONResponse(
            status_code=status.HTTP_200_OK, 
            content={"message": "Client updated successfully", "data": updated_client}
        )

    except HTTPException as e:
        raise e 

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Delete client
@motorapi_router.delete("/delete-client/{client_id}")
async def delete_client(
    client_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")

        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        client = client_collection.find_one({"_id": objid(client_id), "is_deleted": {"$ne": True}})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found or already deleted")

        update_result = client_collection.update_one(
            {"_id": objid(client_id)},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.now(timezone.utc)
                }
            }
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Client deletion failed")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Client deleted successfully"}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Restore client
@motorapi_router.post("/restore-client/{client_id}")
async def restore_client(
    client_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")

        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        client = client_collection.find_one({"_id": objid(client_id), "is_deleted": True})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found or not deleted")

        update_result = client_collection.update_one(
            {"_id": objid(client_id)},
            {
                "$set": {
                    "is_deleted": False,
                    "restored_at": datetime.now(timezone.utc)
                }
            }
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Client restore failed")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Client restored successfully"}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# Get chat history
@motorapi_router.get("/chat-history/{sender}/{receiver}", response_model=List[MessageOut])
async def get_chat_history(sender: str, receiver: str):
    messages =  messages_collection.find({
        "$or": [
            {"sender_id": sender, "receiver_id": receiver},
            {"sender_id": receiver, "receiver_id": sender}
        ]
    }).sort("timestamp", 1).to_list(length=100)

    return messages
    
# Mark message as read
@motorapi_router.put("/read-message/{message_id}")
async def read_message(message_id: str):
    await mark_as_read(message_id)
    return {"status": "marked as read"}

# Upload file for chat
@motorapi_router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        filename = f"{uuid4()}_{file.filename}"
        file_url =  upload_to_s3(file,filename)  # implement this
        return {"file_url": file_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    



#add aiagent    
@motorapi_router.post("/add-aiagent")
async def add_ai_agent(
    place_of_appear: str = Form(...), 
    ai_model_file: UploadFile = File(...)
):
    try:
        # Generate unique filename
        filename = f"{uuid4()}_{ai_model_file.filename}"
        
        
        file_url = upload_to_s3(ai_model_file, filename)

        # Prepare MongoDB data
        data = {
            "place_of_appear": place_of_appear,
            "file_url": file_url
        }

        # Insert into MongoDB
        result = ai_agent_collection.insert_one(data)

        # Return response
        return {
            "id": str(result.inserted_id),
            "place_of_appear": place_of_appear,
            "file_url": file_url
        }

    except Exception as e:
        print(f"❌ Error: {e}")  # helpful in dev
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

#get all aiagents  
@motorapi_router.get("/get-all-aiagents")
async def get_all_ai_agents(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        skip = (page - 1) * limit
        total_count = ai_agent_collection.count_documents({})

        cursor = ai_agent_collection.find().skip(skip).limit(limit)
        agents =  cursor.to_list(length=limit)

        data = [
            {
                "id": str(agent["_id"]),
                "place_of_appear": agent["place_of_appear"],
                "file_url": agent["file_url"]
            }
            for agent in agents
        ]

        return JSONResponse(
            status_code=200,
            content={
                "message": "AI agents fetched successfully",
                "data": data,
                "page_info": {
                    "page": page,
                    "limit": limit,
                    "total_pages": total_count,
                    "total_records": (total_count + limit - 1) // limit
                }
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@motorapi_router.put("/update-aiagent/{agent_id}")
async def update_ai_agent(
    agent_id: str,
    place_of_appear:Optional[str] = Form(None),
    ai_model_file: Optional[UploadFile] = File(None)
):
    update_data = {}

    if place_of_appear:
        update_data["place_of_appear"] = place_of_appear

    if ai_model_file:
        filename = f"{uuid4()}_{ai_model_file.filename}"
        file_url = upload_to_s3(ai_model_file, filename)
        update_data["ai_model_file"] = file_url

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    result = ai_agent_collection.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="AI Agent not found or no change")

    return {
        "status": True,
        "message": "AI Agent updated successfully",
        "updated_fields": update_data
    }
#delete aiagent
@motorapi_router.delete("/delete-aiagent/{agent_id}")
async def delete_ai_agent(agent_id: str):
    result = ai_agent_collection.delete_one({"_id": ObjectId(agent_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="AI Agent not found")
    return {"message": "AI Agent deleted successfully"}




#add homefeatureditems
@motorapi_router.post("/add-HomeFeaturedItems")
async def add_home_featured_items(
    title:str=Form(...),
    image_file: UploadFile = File(...),
    link:str=Form(...),
    ):
    try:
        # Generate unique filename
        filename = f"{uuid4()}_{image_file.filename}"
        
        # Upload file to S3
        file_url = upload_to_s3(image_file,filename)

        # Prepare MongoDB data
        data = {
            "title": title,
            "image_file": file_url,
            "link": str(link)
        }

        # Insert into MongoDB
        result = home_featured_items.insert_one(data)

        # Return response
        return {
            "title": title,
            "image_file": file_url,
            "link": str(link)
        }

    except Exception as e:
     traceback.print_exc()  
     raise HTTPException(status_code=500, detail=str(e)) 

#get all homefeatureditems
@motorapi_router.get("/get-all-homefeatureditems")
async def get_all_home_featured_items(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        skip = (page - 1) * limit
        total_count = home_featured_items.count_documents({})

        cursor = home_featured_items.find().skip(skip).limit(limit)
        items =  cursor.to_list(length=limit)

        data = [
            {
                "id": str(item["_id"]),
                "title": item["title"],
                "image_file": item["image_file"],
                "link": item["link"]
            }
            for item in items
        ]

        return JSONResponse(
            status_code=200,
            content={
                "message": "Home featured items fetched successfully",
                "data": data,
                "page_info": {
                    "page": page,
                    "limit": limit,
                    "total_pages": total_count,
                    "total_records": (total_count + limit - 1) // limit  # total pages
                }
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#update homefeatureditems
@motorapi_router.put("/update-homefeatureditem/{item_id}")
async def update_home_featured_item(
    item_id: str,
    title: Optional[str] = Form(None),
    link: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None)  
):
    try:
        item = home_featured_items.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        update_data = {}

        if title:
            update_data["title"] = title
        if link:
            update_data["link"] = link
        if image_file:
            filename = f"{uuid4()}_{image_file.filename}"
            file_url = upload_to_s3(image_file, filename)
            update_data["image_file"] = file_url

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        home_featured_items.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": update_data}
        )

        return {
            "status": True,
            "message": "Home Featured Item updated successfully",
            "updated_fields": update_data
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    

#delete homefeatureditems
@motorapi_router.delete("/delete-homefeatureditem/{item_id}")
async def delete_home_featured_item(item_id: str):
    result = home_featured_items.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Home Featured Item not found")
    return {"message": "Home Featured Item deleted successfully"}


#add privacy
@motorapi_router.post("/privacy")
async def create_privacy_policy(payload: PrivacyPolicy, user: str = Depends(get_current_user)):
    existing = privacy_collection.find_one()
    if existing:
        raise HTTPException(status_code=400, detail="Privacy Policy already exists. Use update instead.")
    
    doc = payload.dict()
    privacy_collection.insert_one(doc)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Privacy Policy created successfully"}
    )

#update privacy
@motorapi_router.put("/privacy-update")
async def update_privacy_policy(payload: PrivacyPolicy, user: dict = Depends(get_current_user)):
    # Allow only admin and superuser
    if user["role"] not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Find existing document
    existing =  privacy_collection.find_one({})
    if not existing:
        raise HTTPException(status_code=404, detail="Privacy Policy not found.")

    # Update it by _id
    privacy_collection.update_one(
        {"_id": existing["_id"]},
        {"$set": payload.dict()}
    )

    return {"message": "Privacy Policy updated successfully"}

#get-all-privacy
@motorapi_router.get("/list-all-privacy")
async def get_privacy_policy():
    doc = privacy_collection.find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Privacy Policy not found.")
    return get(doc)

#create about us
@motorapi_router.post("/about-us")
async def create_about_us(
    payload: AboutUsSchema,
    user: dict = Depends(get_current_user)
):
    if user["role"] not in ["admin", "superadmin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    existing =  about_us_collection.find_one({})
    if existing:
        raise HTTPException(status_code=400, detail="About Us already exists. Please update instead.")

    about_us_collection.insert_one(payload.dict())
    return {"message": "About Us created successfully"}

#update about us
@motorapi_router.put("/about-us-update")
async def update_about_us(
    payload: AboutUsSchema,
    user: dict = Depends(get_current_user)
):
    if user["role"] not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    existing =  about_us_collection.find_one({})
    if not existing:
        raise HTTPException(status_code=404, detail="About Us not found.")

    about_us_collection.update_one(
        {"_id": existing["_id"]},
        {"$set": payload.dict()}
    )

    return {"message": "About Us updated successfully"}

#list all about us
@motorapi_router.get("/list-all-about-us")
async def get_about_us():
    doc = about_us_collection.find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="About Us not found.")
    return get(doc)

#create bottom slider
@motorapi_router.post("/bottom-slider")
async def create_bottom_slider(
    title: str=Form(...),
    image_file: list[UploadFile] = File(...),
    user: dict = Depends(get_current_user)
):
    if user["role"] not in ["admin", "superadmin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    image_urls = []
    for file in image_file:

        file_ext = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        s3_url = upload_to_s3(file, unique_filename)
        image_urls.append(s3_url)

    slider_data = {
        "title": title,
        "images": image_urls
    }

    result = bottom_slider_collection.insert_one(slider_data)
    slider_data["_id"] = result.inserted_id

    return {"message": "Bottom Slider created successfully", "data": get(slider_data)}

#update bottom slider
@motorapi_router.put("/update-bottom-slider/{slider_id}")
async def update_bottom_slider(
    slider_id: str,
    title: Optional[str] = Form(...),
    image_file: Optional[List[UploadFile]] = File(None),
    user: dict = Depends(get_current_user)
):
    if user["role"] not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    slider = bottom_slider_collection.find_one({"_id": objid(slider_id)})
    if not slider:
        raise HTTPException(status_code=404, detail="Bottom Slider not found")

    update_data = {}

    if title:
        update_data["title"] = title

    if image_file:
        image_urls = []
        for file in image_file:
            file_ext = file.filename.split(".")[-1]
            unique_filename = f"{uuid.uuid4()}.{file_ext}"
            s3_url = upload_to_s3(file, unique_filename)
            image_urls.append(s3_url)
        update_data["images"] = image_urls

    if update_data:
         bottom_slider_collection.update_one(
            {"_id": objid(slider_id)},
            {"$set": update_data}
        )

   
    updated_slider =  bottom_slider_collection.find_one({"_id": objid(slider_id)})

    return {"message": "Bottom Slider updated successfully", "data": get(updated_slider)}

#list all bottom slider
@motorapi_router.get("/list-all-bottom-slider")
async def get_bottom_slider():
    cursor = bottom_slider_collection.find({"is_deleted": {"$ne": True}})
    docs = []
    for doc in cursor:
        docs.append(get(doc))
    
    if not docs:
        raise HTTPException(status_code=404, detail="No bottom sliders found.")

    return {"data": docs}

#delete bottom slider
@motorapi_router.delete("/delete-bottom-slider/{slider_id}")
async def delete_bottom_slider(slider_id: str, user: dict = Depends(get_current_user)):
    if user["role"] not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    slider =  bottom_slider_collection.find_one({"_id": objid(slider_id)})
    if not slider:
        raise HTTPException(status_code=404, detail="Bottom Slider not found")

    bottom_slider_collection.update_one(
        {"_id": objid(slider_id)},
        {"$set": {"is_deleted": True}}
    )

    return {"message": "Bottom Slider deleted successfully (soft delete)"}

#create settings
@motorapi_router.post("/settings")
async def create_settings(
    payload: SettingsSchema,
    user: dict = Depends(get_current_user)
):
    if user["role"] not in ["admin", "superadmin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    existing =settings_collection.find_one({})
    if existing:
        settings_collection.update_one(
            {"_id": existing["_id"]},
            {"$set": payload.dict()}
        )
        updated =settings_collection.find_one({"_id": existing["_id"]})
        return {"message": "Settings updated successfully", "data": get(updated)}
    else:
        result = settings_collection.insert_one(payload.dict())
        created = settings_collection.find_one({"_id": result.inserted_id})
        return {"message": "Settings created successfully", "data": get(created)}

#get all settings
@motorapi_router.get("/get-all-settings")
async def get_settings(option: str = Query(..., regex="^(header|footer)$")):
    cursor = settings_collection.find({"is_deleted": {"$ne": True}})
    docs = []
    for doc in cursor:
        doc=get(doc)
        if option == "header":
            docs.append({
                "email": doc.get("email"),
                "whatsapp": doc.get("whatsapp"),
                "videos": doc.get("videos")
            })
        elif option == "footer":
            docs.append({
                "app_links": doc.get("app_links"),
                "social_links": doc.get("social_links")
            })
        if not docs:
            raise HTTPException(status_code=404, detail="No settings found.")
    return {"data": docs}

#delete settings(soft delete)
@motorapi_router.delete("/delete-settings/{settings_id}")
async def delete_settings(settings_id: str, user: dict = Depends(get_current_user)):
    if user["role"] not in ["admin", "superadmin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    
    settings = settings_collection.find_one({
        "_id": objid(settings_id),
        "is_deleted": {"$ne": True}
    })

    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Soft delete by setting is_deleted = True
    settings_collection.update_one(
        {"_id": objid(settings_id)},
        {"$set": {"is_deleted": True}}
    )

    return {"message": "Settings deleted successfully (soft delete)"}

@motorapi_router.post("/faq")
async def create_faq(title: str=Form(...), content: str=Form(...), type:FAQType=Form(...), user: dict = Depends(get_current_user)):
    if user["role"] not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    faq_data = {
        "title": title,
        "content": content,
        "type": type.lower(),  # store consistently
        "is_deleted": False
    }

    result = faq_collection.insert_one(faq_data)
    created = faq_collection.find_one({"_id": result.inserted_id})
    return {"message": "FAQ created successfully", "data": get(created)}

@motorapi_router.get("/get-all-faqs")
async def get_all_faqs(type: FAQType = Query(...)):
    cursor = faq_collection.find({
        "is_deleted": {"$ne": True},
        "type": type
    })

    docs = [get(doc) for doc in cursor]

    if not docs:
        raise HTTPException(status_code=404, detail="No FAQs found.")

    return {"data": docs}


@motorapi_router.put("/update-faq/{faq_id}")
async def update_faq(
    faq_id: str,
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    type: Optional[FAQType] = Form(None),
    user: dict = Depends(get_current_user)
):
    
    if user["role"] not in ["admin", "superadmin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    faq =faq_collection.find_one({
        "_id": objid(faq_id),
        "is_deleted": {"$ne": True}
    })

    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if content is not None:
        update_data["content"] = content
    if type is not None:
        update_data["type"] = type.value

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")


    faq_collection.update_one(
        {"_id": objid(faq_id)},
        {"$set": update_data}
            
        
    )

    updated =faq_collection.find_one({"_id": objid(faq_id)})
    return {"message": "FAQ updated successfully", "data": get(updated)}


@motorapi_router.delete("/delete-faq/{faq_id}")
async def delete_faq(faq_id: str, user: dict = Depends(get_current_user)):
    if user["role"] not in ["admin", "superadmin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    faq = faq_collection.find_one({
        "_id": objid(faq_id),
        "is_deleted": {"$ne": True}
    })

    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    
    faq_collection.update_one(
        {"_id": objid(faq_id)},
        {"$set": {"is_deleted": True}}
    )

    return {"message": "FAQ deleted successfully (soft delete)"}