import json
import os
import re
import shutil
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Body, File, Form, HTTPException, Query, Request, UploadFile, status,Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.database.db import car_collection, agent_collection,company_collection,vehicle_type_collection,car_brand_collection
from app.models.car.car import AddCar, UpdateCar
from datetime import datetime, timezone
from app.utilities.convert_object_id import convert_datetime, convert_object_ids, objid
from app.utilities.helper import refresh_agent_listing
from app.utilities.security import decode_jwt_token, get_current_user,get,get_next_row_number
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME,S3_BUCKET_URL 
from app.services.S3 import upload_to_s3
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME, S3_BUCKET_URL
import boto3
from pymongo import ASCENDING, DESCENDING

from mimetypes import guess_type
car_router = APIRouter(
    prefix="/admin/car-api",
    tags=["CarAPI"],
)


# Add car brand
@car_router.post("/add-car-brand")
async def add_car_brand(
    request: Request,
    car_brand: str = Form(...),
    logo: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Authorization check
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to add car brands.")

        # Normalize brand name
        normalized_brand = car_brand.strip().lower().capitalize()

        # Check for existing brand (case insensitive)
        existing = car_brand_collection.find_one({
            "brand": {"$regex": f"^{normalized_brand}$", "$options": "i"}
        })
        if existing:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "Car brand already exists"}
            )

        # Handle logo upload
        logo_url = None
        if logo:
            image_ext = logo.filename.split(".")[-1]
            filename = f"brand_{normalized_brand.replace(' ', '_')}.{image_ext}"

            logo_url =upload_to_s3(logo, filename)
        # Insert new brand
        brand_doc = {
            "brand": normalized_brand,
            "logo": logo_url,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        insert_result = car_brand_collection.insert_one(brand_doc)
        brand_doc["_id"] = str(insert_result.inserted_id)  # Convert ObjectId to string

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Car brand added successfully", "data": jsonable_encoder(brand_doc)}
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all car brands
@car_router.get("/car-brands")
async def get_all_car_brands(request: Request,
    # current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    
    try:
       
        query = {"is_deleted": {"$ne": True}}
        skip = (page - 1) * limit
       # Apply pagination to the cursor
        brands_cursor = car_brand_collection.find(query).skip(skip).limit(limit)
        brands = []

        for brand in brands_cursor:
            brand_id = str(brand["_id"])
            cars_count = car_collection.count_documents({"basic_info.brand_id": brand_id})

            brand["car_count"] = cars_count
            brands.append(convert_object_ids(brand))

            total_count = car_brand_collection.count_documents(query)
            total_pages = (total_count + limit - 1) // limit

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Car brands fetched successfully",
                      "data": brands,
                      "page_info": {
                    "page": page,
                    "limit": limit,
                    "total_records": total_count,
                    "total_pages": total_pages
                }}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update car brand
@car_router.put("/update-car-brand/{brand_id}")
async def update_car_brand(
    request: Request,
    brand_id: str,
    car_brand: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    logo_url: Optional[str] = Form(None),  
    current_user: dict = Depends(get_current_user)
):
    try:
        # Authorization
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to update car brands.")

        # Validate ObjectId
        try:
            brand_obj_id = ObjectId(brand_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid brand ID")

        update_fields = {"updated_at": datetime.utcnow()}

        # Handle car brand update (if provided)
        if car_brand:
            normalized_brand = car_brand.strip().lower().capitalize()

            existing = car_brand_collection.find_one({
                "brand": {"$regex": f"^{normalized_brand}$", "$options": "i"}
            })
            if existing and str(existing["_id"]) != brand_id:
                raise HTTPException(status_code=400, detail="Car brand already exists")

            update_fields["brand"] = normalized_brand

        # Handle logo upload (if provided)
        if logo:
            image_ext = logo.filename.split(".")[-1]
            filename = f"brand_{brand_id}.{image_ext}"
            uploaded_logo_url = upload_to_s3(logo, filename)
            update_fields["logo"] = uploaded_logo_url

        # Case 2: URL provided (only if file not sent)
        elif logo_url:
            update_fields["logo"] = logo_url

        # If no fields provided, reject update
        if len(update_fields) == 1:  # Only updated_at
            raise HTTPException(status_code=400, detail="No data provided to update.")

        # Perform update
        update_result = car_brand_collection.update_one(
            {"_id": brand_obj_id},
            {"$set": update_fields}
        )

        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Car brand not found")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Car brand updated successfully"}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add vehicle type
@car_router.post("/add-vehicle-type")
async def add_vehicle_type(
    request: Request,
    vehicle_type: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to add vehicle types.")

        vehicle_type_doc = {
            "type": vehicle_type,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        insert_result = vehicle_type_collection.insert_one(vehicle_type_doc)
        vehicle_type_doc["_id"] = str(insert_result.inserted_id) 

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Vehicle type added successfully", "data": vehicle_type_doc}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))     

# Get all vehicle types
@car_router.get("/get-vehicle-type")
async def get_vehicle_type():
    try:
        vehicle_types = list(vehicle_type_collection.find())
        
        for vt in vehicle_types:
            vt["_id"] = str(vt["_id"])
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": vehicle_types}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add Car
@car_router.post("/add-car")
async def add_car(
    request: Request,
    car_details: str = Form(...),
    car_images: Optional[List[UploadFile]] = File(None),
    images: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        is_admin = role in ["admin", "superuser"]

        if role not in ["admin", "superuser", "agent"]:
            raise HTTPException(status_code=403, detail="You are not authorized to add cars")

        request_body = AddCar.model_validate(json.loads(car_details))

        company = None
        agent = None

        if request_body.agent_id:
            agent = agent_collection.find_one({"_id": objid(request_body.agent_id)})
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            if agent.get("status") != "approved" and not is_admin:
                raise HTTPException(status_code=403, detail="Agent is not approved to add cars")

            company_id = agent.get("company_id")
            if not company_id:
                raise HTTPException(status_code=400, detail="Agent is not linked to any company")
            company = company_collection.find_one({"_id": objid(company_id)})
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")
        else:
            if not is_admin:
                raise HTTPException(status_code=400, detail="Only admin/superuser can add cars without agent")
            if not request_body.company_id:
                raise HTTPException(status_code=400, detail="company_id is required for admin/superuser car creation")

            company = company_collection.find_one({"_id": objid(request_body.company_id)})
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

        brand_id = request_body.basic_info.brand_id
        if not brand_id:
            raise HTTPException(status_code=400, detail="brand_id is required in basic_info")
        brand_doc = car_brand_collection.find_one({"_id": objid(brand_id)})
        if not brand_doc:
            raise HTTPException(status_code=404, detail=f"Brand with id '{brand_id}' not found")

        if request_body.vehicle_type:
            vehicle_docs = vehicle_type_collection.find()
            valid_types = {doc["type"] for doc in vehicle_docs}
            for vt in request_body.vehicle_type:
                if vt not in valid_types:
                    raise HTTPException(status_code=400, detail=f"Invalid vehicle type: {vt}")
                
        duplicate_query = {
            "basic_info.brand_id": request_body.basic_info.brand_id,
            "basic_info.model": request_body.basic_info.model,
            "basic_info.year": request_body.basic_info.year,
            "company_id": str(company["_id"]),
        }

        if agent:
            duplicate_query["agent_id"] = str(agent["_id"])

        existing_car = car_collection.find_one(duplicate_query)
        if existing_car:
            raise HTTPException(
                status_code=400, detail="A car with the same brand, model, and year already exists under this company."
            )

        temp_images=''
        if images:
            # for index, image in enumerate(images):
            image_ext = images.filename.split(".")[-1]
            filename = f"{company['_id']}_car.{image_ext}"
            url = upload_to_s3(images,filename)
            temp_images=url

        # print('car_images',car_images)
        image_url = []
        if car_images:
         for index, image in enumerate(car_images):
                image_ext = image.filename.split(".")[-1]
                filename = f"{company['_id']}_car_{index}.{image_ext}"
                url = upload_to_s3(image,filename)
                image_url.append(url)
        car_data = request_body.model_dump()
        car_data["basic_info"]["brand"] = brand_doc["brand"]

        if agent:
            car_data["agent_id"] = str(agent["_id"])
            car_data["agent_name"] = agent["first_name"]+' '+agent["last_name"]
            car_data["agent_email"] = agent["email"]

        # Role-based status assignment
        if is_admin:
            car_data["status"] = "approved"
        elif role == "agent":
            car_data["status"] = "pending"

        car_data["creator_role"] = role
        car_data["company_id"] = str(company["_id"])
        car_data["company_name"] = company.get("name", "Unknown")
        car_data["created_by"] = current_user["username"]
        car_data["email"] = current_user["email"]
        car_data["images"] = temp_images
        car_data["car_images"] = image_url
        car_data["company_logo"] = company.get("logo_url", "Unknown")
        car_data["created_at"] = datetime.now(timezone.utc).isoformat()

        row_number = get_next_row_number()
        car_data["meta_data"] = {
            "row_number": row_number,
            "status": False,
            "description": "Car listing metadata for MotorsFinder platform.",
            "domain_id": "car.motorsfinder.ai"
        }

        insert_result = car_collection.insert_one(car_data)
        car_data["_id"] = str(insert_result.inserted_id)
        if agent:                           
            refresh_agent_listing(agent["_id"])

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Car added successfully", "data": car_data}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#list all cars
def serialize_car(car):
    car["_id"] = str(car["_id"])
    if "company_id" in car:
        car["company_id"] = str(car["company_id"])
    if "agent_id" in car:
        car["agent_id"] = str(car["agent_id"])
    for key, value in car.items():
        if isinstance(value, datetime):
            car[key] = value.isoformat()
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    for k, v in item.items():
                        if isinstance(v, datetime):
                            item[k] = v.isoformat()
    return car

@car_router.get("/list-all-cars")
def list_all_cars(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query(None, regex="^(price|created_at)?$"),
    order: str = Query(None, regex="^(asc|desc)?$")
):
    try:
       

        skip = (page - 1) * limit
        query = {}
        total_cars = car_collection.count_documents({})
        total_pages = (total_cars + limit - 1) // limit

        sort_order = None
        if sort_by and order:
            direction = ASCENDING if order == "asc" else DESCENDING
            sort_order = [(sort_by, direction)]

        # Apply sorting, skipping, and limiting
        if sort_order:
            cursor = car_collection.find(query).sort(sort_order).skip(skip).limit(limit)
        else:
            cursor = car_collection.find(query).skip(skip).limit(limit)

        # cursor = car_collection.find({}).skip(skip).limit(limit)

        # cars = []
        cars = [serialize_car(car) for car in cursor]
        

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "List of all cars",
                "data": cars,
                "page_info": {
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                    "total_records": total_cars
                }
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

#Agent List all cars with count
@car_router.get("/list-cars")
async def list_all_cars(
    # current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100)
):
    try:
        
        query = {"is_deleted": {"$ne": True}}
 
        total_cars = car_collection.count_documents(query)
        total_pages = (total_cars + limit - 1) // limit
        skip = (page - 1) * limit
 
        cars_cursor = car_collection.find(query).skip(skip).limit(limit)
        cars = []
 
        for car in cars_cursor:
            car["_id"] = str(car["_id"])
            if "company_id" in car:
                car["company_id"] = str(car["company_id"])
            if "agent_id" in car:
                car["agent_id"] = str(car["agent_id"])
            cars.append(convert_datetime(car))
 
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "List of cars",
                "data": cars,
                "page_info": {
                    "page": page,
                    "count": len(cars),
                    "limit": limit,
                    "total_pages": total_pages,
                    "total_records": total_cars
                }
            }
        )
 
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Get all cars by company
@car_router.get("/all-cars-by-company/{company_id}")
async def get_all_cars_by_company(
    company_id: str,
    price: str = Query(None, pattern="^(low|high)?$"),
    date: str = Query(None, pattern="^(asce|desc)?$"),
    vehicle_type: str = Query(None, pattern="^(rent|sell|buy)?$")
):
    try:
        # Prepare base query
        query = {
            "company_id": company_id,
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        }

        if vehicle_type:
            query["vehicle_type"] = vehicle_type.lower()

        # Build sorting
        sort_order = []
        if price:
            sort_order.append(("basic_info.price", ASCENDING if price == "low" else DESCENDING))
        if date:
            sort_order.append(("created_at", ASCENDING if date == "asce" else DESCENDING))

        # Run MongoDB query with or without sort
        cursor = car_collection.find(query)
        if sort_order:
            cursor = cursor.sort(sort_order)

        cars = [get(car) for car in cursor]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Cars fetched successfully",
                "cars": cars,
                "total": len(cars)
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )

# Get a specific car by ID
@car_router.get("/get-car/{car_id}")
async def get_car(
    car_id: str,
    request: Request,
):
    try:

        # Fetch car
        car = car_collection.find_one({"_id": objid(car_id)})
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")

        car["_id"] = str(car["_id"])

        clean_car = get(car)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": car}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Approve car 
@car_router.post("/approve-car/{car_id}")
async def approve_car(
    car_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to approve cars.")

        # First try approving pending cars
        result = car_collection.update_one(
            {"_id": objid(car_id), "status": "pending"},
            {
                "$set": {
                    "status": "approved",
                    "updated_by": current_user["username"],
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.modified_count == 0:
            # Try approving rejected cars if flagged for re-verification
            result = car_collection.update_one(
                {"_id": objid(car_id), "status": "rejected", "reverification": True},
                {
                    "$set": {
                        "status": "approved",
                        "reverification": False,
                        "updated_by": current_user["username"],
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="No pending or rejected car found for approval.")

        updated_car = car_collection.find_one({"_id": objid(car_id)})
        updated_car = convert_object_ids(updated_car)
        encoded_car = jsonable_encoder(updated_car)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Car approved successfully", "data": encoded_car}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Reject car 
@car_router.post("/reject-car/{car_id}")
async def reject_car(
    car_id: str,
    rejection_reason: str = Body(..., embed=True),  
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to reject cars.")

        # Update the car's status and add rejection reason
        result = car_collection.update_one(
            {"_id": objid(car_id), "status": "pending"},
            {
                "$set": {
                    "status": "rejected",
                    "rejection_reason": rejection_reason,
                    "updated_by": current_user["username"],
                    "updated_at": datetime.now(timezone.utc),
                    "reverification": True  # flag for re-verification flow
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="No pending car found to reject.")

        updated_car = car_collection.find_one({"_id": objid(car_id)})
        updated_car = convert_object_ids(updated_car)
        encoded_car = jsonable_encoder(updated_car)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Car rejected successfully, pending reverification", "data": encoded_car}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update a car
@car_router.put("/update-car/{car_id}")
async def update_car(
    request: Request,
    car_id: str,
    car_details: Optional[str] = Form(None),
    images: Optional[UploadFile] = File(None),
    car_images: Optional[List[UploadFile]] = File(None),
    images_urls: Optional[List[str]] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        car = car_collection.find_one({"_id": objid(car_id)})
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")

        user_role = current_user.get("role")
        if user_role not in ["admin", "superuser", "agent"]:
            raise HTTPException(status_code=403, detail="Unauthorized role")

        updated_data = {}
        if car_details:
            request_body = UpdateCar.model_validate(json.loads(car_details))
            updated_data = {
                k: v for k, v in request_body.model_dump(exclude_unset=True).items() if v is not None
            }

        if not updated_data and not images and not car_images and not images_urls:
            raise HTTPException(status_code=400, detail="No valid fields or images provided")

        # Set status based on user role
        if user_role in ["admin", "superuser"]:
            updated_data["status"] = "approved"
        elif user_role == "agent":
            updated_data["status"] = "pending"

        company_id = car.get("company_id", "unknown_company")

        # ✅ Upload primary image
        if images and user_role in ["admin", "superuser"]:
            ext = images.filename.split(".")[-1]
            filename = f"{car_id}_images_{int(datetime.utcnow().timestamp())}.{ext}"
            file = f"car/{company_id}/{filename}"
            url = upload_to_s3(file=images, filename=file)
            updated_data["images"] = url

         # ✅ Handle multiple car images
        image_urls = car.get("car_images", [])

        # Upload new image files
        if car_images and user_role in ["admin", "superuser"]:
            for index, image_file in enumerate(car_images):
                ext = image_file.filename.split(".")[-1]
                filename = f"{car_id}_{int(datetime.utcnow().timestamp())}_{index}.{ext}"
                s3_key = f"car/{company_id}/{filename}"
                url = upload_to_s3(file=image_file, filename=s3_key)
                image_urls.append(url)

        # Add existing image URLs
        if images_urls:
            image_urls.extend(images_urls)

        if image_urls:
            updated_data["car_images"] = image_urls

        # Flatten nested dict
        def flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        flattened_data = flatten_dict(updated_data)
        flattened_data["updated_at"] = datetime.now(timezone.utc)

        car_collection.update_one({"_id": objid(car_id)}, {"$set": flattened_data})

        flattened_data["updated_at"] = flattened_data["updated_at"].isoformat()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Car updated successfully", "data": flattened_data}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Soft-delete a car
@car_router.delete("/delete-car/{car_id}")
async def delete_car(
    car_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_role = current_user.get("role")
        if user_role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="Unauthorized role")

        car = car_collection.find_one({"_id": objid(car_id)})
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")

        if car.get("is_deleted", False):
            raise HTTPException(status_code=400, detail="Car already deleted")

        car_collection.update_one(
            {"_id": objid(car_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )

        return JSONResponse(
            status_code=200,
            content={"message": "Car deleted successfully"}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@car_router.post("/restore-car/{car_id}")
async def restore_car(
    car_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_role = current_user.get("role")
        if user_role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="Unauthorized role")

        car = car_collection.find_one({"_id": objid(car_id)})
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")

        if not car.get("is_deleted", False):
            raise HTTPException(status_code=400, detail="Car is not deleted")

        car_collection.update_one(
            {"_id": objid(car_id)},
            {"$set": {"is_deleted": False, "deleted_at": None}}
        )

        return JSONResponse(
            status_code=200,
            content={"message": "Car restored successfully"}
        )
    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

