import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from app.models.review.review import CarReview 
from app.database.db import car_collection, client_collection, review_collection
from bson import ObjectId as objid
from app.services.S3 import upload_to_s3
from app.utilities.convert_object_id import convert_object_ids
from app.utilities.security import get_current_user
from app.services.json import return_json, return_error_json

review_router = APIRouter(
    prefix="/review",
    tags=["ReviewAPI"], 
)

# Client Add the Review
@review_router.post("/add-review")
async def add_car_review(
    request: Request,
    car_id: str = Form(...),
    rating: float = Form(...),
    review: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Validate role
        role = current_user.get("role")
        if role != "client":
            raise HTTPException(status_code=403, detail="Only clients can submit reviews")

        # Find client
        client_email = current_user.get("email")
        client_details = client_collection.find_one({"email": client_email})
        if not client_details:
            raise HTTPException(status_code=404, detail="Client not found")

        # Check car existence
        car = car_collection.find_one({"_id": objid(car_id)})
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")

        # Handle images
        image_urls = []

        if images:
         for index, image in enumerate(images):
          ext = image.filename.split('.')[-1]
          filename = f"review_{str(client_details['_id'])}_{index}.{ext}"
          image_url = upload_to_s3(image, filename)
          image_urls.append(image_url)

        # Construct review document
        review_doc = {
            "car_id": car_id,
            "client_id": str(client_details["_id"]),
            "client_name": client_details.get("name", "Anonymous"),
            "rating": rating,
            "review": review,
            "status": "pending",
            "is_deleted": False,
            "images": image_url,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        insert_result = review_collection.insert_one(review_doc)
        review_doc["_id"] = str(insert_result.inserted_id)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Review submitted successfully", "data": review_doc}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Admin and Superuser List all the Review
@review_router.get("/all-reviews")
async def list_all_client_reviews(
    # current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        # # Check user role
        # role = current_user.get("role")
        # if role not in ["admin", "superuser"]:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="You are not authorized to view all reviews."
        #     )

        skip = (page - 1) * limit

        query = {}  # <- show all reviews, including deleted or any status
        total_reviews = review_collection.count_documents(query)
        total_pages = (total_reviews + limit - 1) // limit

        reviews_cursor = review_collection.find(query).skip(skip).limit(limit)

        reviews = []
        for review in reviews_cursor:
            review["_id"] = str(review["_id"])
            if "car_id" in review:
                review["car_id"] = str(review["car_id"])
            if "client_id" in review:
                review["client_id"] = str(review["client_id"])
            if "created_at" in review and isinstance(review["created_at"], datetime):
                review["created_at"] = review["created_at"].isoformat()
            reviews.append(review)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "List of all client reviews",
                "data": reviews,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                    "total_records": total_reviews,
                }
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Client List the Review
@review_router.get("/my-reviews")
async def list_client_reviews(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        role = current_user.get("role")
        if role != "client":
            raise HTTPException(status_code=403, detail="Unauthorized access")

        # Get client from database based on email
        client = client_collection.find_one({"email": current_user.get("email")})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        client_id = str(client["_id"])
        query = {"client_id": client_id}

        total_reviews = review_collection.count_documents(query)
        total_pages = (total_reviews + limit - 1) // limit
        skip = (page - 1) * limit

        reviews_cursor = review_collection.find(query).skip(skip).limit(limit)

        reviews = []
        for review in reviews_cursor:
            review["_id"] = str(review["_id"])
            review["created_at"] = review.get("created_at")
            review["car_id"] = str(review.get("car_id"))
            reviews.append(review)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "List of your reviews",
                "data": reviews,
                "page_info": {
                    "page": page,
                    "limit": limit,
                    "total_reviews": total_reviews,
                    "total_pages": total_pages
                }
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Admin Approve the Review
@review_router.post("/approve-review/{review_id}")
async def approve_review(
    review_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to approve reviews.")

        # Approve only if review status is pending
        result = review_collection.update_one(
            {"_id": objid(review_id), "status": "pending"},
            {
                "$set": {
                    "status": "approved",
                    "updated_by": current_user["username"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="No pending review found for approval.")

        updated_review = review_collection.find_one({"_id": objid(review_id)})
        updated_review = convert_object_ids(updated_review)
        encoded_review = jsonable_encoder(updated_review)

        return JSONResponse(
            status_code=200,
            content={"message": "Review approved successfully", "data": encoded_review}
        )

    except HTTPException as e:
        raise e 

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Admin Reject the Review   
@review_router.post("/reject-review/{review_id}")
async def reject_review(
    review_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to reject reviews.")

        # Reject only if review status is pending
        result = review_collection.update_one(
            {"_id": objid(review_id), "status": "pending"},
            {
                "$set": {
                    "status": "rejected",
                    "updated_by": current_user["username"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="No pending review found for rejection.")

        updated_review = review_collection.find_one({"_id": objid(review_id)})
        updated_review = convert_object_ids(updated_review)
        encoded_review = jsonable_encoder(updated_review)

        return JSONResponse(
            status_code=200,
            content={"message": "Review rejected successfully", "data": encoded_review}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Admin Soft Delete the Review
@review_router.delete("/delete-review/{review_id}")
async def soft_delete_review(
    review_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        role = current_user.get("role")
        if role not in ["admin", "superuser"]:
            raise HTTPException(status_code=403, detail="You are not authorized to delete reviews.")

        # Find the review first
        review = review_collection.find_one({"_id": objid(review_id)})
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        update_result = review_collection.update_one(
            {"_id": objid(review_id)},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_by": current_user["username"],
                    "deleted_at": datetime.now(timezone.utc),
                }
            }
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to delete review")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Review deleted successfully"}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))