import os
import uuid,boto3
from botocore.exceptions import NoCredentialsError
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, Request, status
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from app.models.category.category import CategoryWithSubcategories
from app.database.db import category_collection
from app.utilities.convert_object_id import objid, convert_object_ids
from app.utilities.security import get_current_user 
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME 
from app.services.S3 import upload_to_s3
category_router = APIRouter(
    prefix="/admin/category",
    tags=["CategoryAPI"],
)


# Add category
@category_router.post("/add-category")
async def add_category(
    data: CategoryWithSubcategories,
    logo: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        print("==============================")
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="Only admin or superuser can add categories")

        existing = category_collection.find_one({"category": data.category})
        if existing:
            raise HTTPException(status_code=400, detail="Category already exists")

        # Build the document
        category_doc = {
            "category": data.category,
            "subcategories": [sub.model_dump() for sub in data.subcategories],
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        result = category_collection.insert_one(category_doc)
        inserted_id = result.inserted_id
        category_doc["_id"] = str(result.inserted_id)

        try:
            if logo:
              filename = f"{inserted_id}_{uuid.uuid4().hex}.{logo.filename.split('.')[-1]}"
              logo_url = upload_to_s3(logo, filename)
              category_collection.update_one({"_id": inserted_id}, {"$set": {"logo_url": logo_url}})
              category_doc["logo_url"] = logo_url

        except NoCredentialsError:
            raise HTTPException(status_code=500, detail="AWS credentials not found.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Logo upload failed: {str(e)}")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Category added successfully", "data": category_doc}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all categories   
@category_router.get("/get-categories")
async def get_categories():
    try:
        categories_cursor = category_collection.find({"is_deleted": {"$ne": True}})
        categories = []
        for category in categories_cursor:
            category["_id"] = str(category["_id"])
            categories.append(category)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": categories}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get category by ID
@category_router.get("/get-category/{category_id}")
async def get_category(category_id: str):
    try:
        category = category_collection.find_one({"_id": objid(category_id)})
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        category["_id"] = str(category["_id"])

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": category}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update category by ID
@category_router.put("/update-category/{category_id}")
async def update_category(category_id: str, data: CategoryWithSubcategories):
    try:
        category = category_collection.find_one({"_id": objid(category_id)})
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        category_collection.update_one({"_id": objid(category_id)}, {"$set": data.model_dump()})
        updated_category = category_collection.find_one({"_id": objid(category_id)})
        updated_category["_id"] = str(updated_category["_id"])

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Category updated successfully", "data": updated_category}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Delete category by ID
@category_router.delete("/delete-category/{category_id}")
async def delete_category(category_id: str, current_user: dict = Depends(get_current_user)):
    try:
        if current_user.get("role") not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="Access denied")

        category = category_collection.find_one({"_id": convert_object_ids(category_id)})
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        category_collection.update_one(
            {"_id": convert_object_ids(category_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}}
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Category deleted successfully"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))