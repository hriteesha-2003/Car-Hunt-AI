import os
import re
import shutil
from typing import List, Optional
import uuid
# from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.database.connections import connect
from app.models.admin.admin import AddAgent, AddClient, AddCompany, UpdateAgent, UpdateClient, UpdateCompany
from app.schemas.schema import get_company_form
from app.utilities.convert_object_id import convert_object_ids, objid
from app.utilities.security import get_current_user,get
from config import DATABASE_NAME, CATEGORY_COLLECTION,ALLOWED_EXTENSIONS
from app.database.db import car_collection, car_brand_collection, company_collection, client_collection,agent_collection,review_collection
from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING


api_router = APIRouter(
    prefix="/motor-api",
    tags=["User API"],
)

#Get all companies.
@api_router.get("/get-all-companies")
async def get_all_companies(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100)
):
    try:
        query = {"is_deleted": {"$ne": True}}
        skip = (page - 1) * limit
        companies_cursor = company_collection.find(query).skip(skip).limit(limit)

        companies = []
        for company in companies_cursor:
            companies.append({
                "_id": str(company["_id"]),
                "name": company.get("name"),
                "about": company.get("about"),
                "category_id": str(company.get("category_id")),
                "subcategory_id": company.get("subcategory_id"),
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
                "logo_url": company.get("logo_url")
            })

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

    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get company using company id
@api_router.get("/get-company/{company_id}")
async def get_company(
    company_id: str, 

):
    try:
        company = company_collection.find_one({"_id": objid(company_id)})
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Format response with full details
        company_data = {
            "_id": str(company["_id"]),
            "name": company.get("name"),
            "about": company.get("about"),
            "category_id": str(company.get("category_id")),
            "subcategory_id": company.get("subcategory_id"),
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
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": company_data}
        )
    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/list-all-cars")
def list_all_cars(
    sort_by_price: str = Query(None, regex="^(low|high)?$"),
    sort_by_date: str = Query(None, regex="^(asce|desc)?$"),
    vehicle_type: str = Query(None,regex="^(rent|sell)?$")
):
    try:
        # Filter out deleted and unapproved cars
        query = {
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        }

        if vehicle_type:
            types_list = [v.strip().lower() for v in vehicle_type.split(",")]
            query["vehicle_type"] = {"$in": types_list}

        # Build sort order
        sort_order = []
        if sort_by_price:
            sort_order.append(("basic_info.price", ASCENDING if sort_by_price == "low" else DESCENDING))
        if sort_by_date:
            sort_order.append(("created_at", ASCENDING if sort_by_date == "asce" else DESCENDING))
        # print("🔍 Sorting by:", sort_order)


        # Build and execute MongoDB query
        if sort_order:
            cursor = car_collection.find(query).sort(sort_order)
        else:
            cursor = car_collection.find(query)

        # Convert MongoDB cursor to response
        cars = [get(car) for car in cursor]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "List of all cars",
                "data": cars,
                "total_cars": len(cars)
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Get car by ID
@api_router.get("/get-car/{car_id}")
async def get_car(car_id: str, request: Request):
    try:
        car = car_collection.find_one({
            "_id": objid(car_id),
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        })

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


# Get all car brands
@api_router.get("/car-brands")
async def s():
    try:
        brands_cursor = car_brand_collection.find({})
        brands = []

        for brand in brands_cursor:
            brand_id = str(brand["_id"])
            cars_count = car_collection.count_documents({"basic_info.brand_id": brand_id})

            brand["car_count"] = cars_count
            brands.append(convert_object_ids(brand))

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Car brands fetched successfully", "data": brands}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#Get list of agents.
@api_router.get("/list-all-agents")
def list_all_agents(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        skip = (page - 1) * limit

        query = {
           "$or": [{"is_deleted": False}, 
                   {"is_deleted": {"$exists": False}}],
            "status": {"$nin": ["pending", "rejected", None]}
        }

        total_agents = agent_collection.count_documents(query) 
        total_pages = (total_agents + limit - 1) // limit

        cursor = agent_collection.find(query).skip(skip).limit(limit)
        agents = [get(agent) for agent in cursor]
        

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "List of all agents",
                "data": agents,
                "page_info": {
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                    "total_agents": total_agents
                }
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Get agent by id.
@api_router.get("/get-agent/{agent_id}")
async def get_agent(agent_id: str, request: Request):
    try:
        agent = agent_collection.find_one({
            "_id": objid(agent_id),
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        })

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent["_id"] = str(agent["_id"])

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
        raise HTTPException(status_code=500, detail=str(e))

#Get list of clients  
@api_router.get("/list-all-clients")
def list_all_clients(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        skip = (page - 1) * limit

        query = {
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        }

        total_clients = client_collection.count_documents(query)
        total_pages = (total_clients + limit - 1) // limit

        cursor = client_collection.find(query).skip(skip).limit(limit)
        clients = []
        for client in cursor:
            client["_id"] = str(client["_id"])
            if "company_id" in client:
                client["company_id"] = str(client["company_id"])
            # you can still optionally isoformat here, but jsonable_encoder covers datetime
            clients.append(client)

        payload = {
            "message": "List of all clients",
            "data": clients,
            "page_info": {
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_clients": total_clients
            }
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(payload)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#Get client by id.
@api_router.get("/get-client/{client_id}")
async def get_client(client_id: str, request: Request):
    try:
        client = client_collection.find_one({
            "_id": objid(client_id),
           "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        })

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Convert _id and other fields if needed
        client["_id"] = str(client["_id"])
        if "company_id" in client:
            client["company_id"] = str(client["company_id"])

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({"data": client})
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Get all Client Review
@api_router.get("/list-all-client-reviews")
async def list_all_client_reviews():
    try:
        query = {
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        }

        cursor = review_collection.find(query)
        reviews = []
        for review in cursor:
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
            content={"message": "List of all client reviews", "data": reviews}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Get Client Review by id
@api_router.get("/get-client-review/{review_id}")
async def get_client_review(review_id: str, request: Request):
    try:
        review = review_collection.find_one({
            "_id": objid(review_id),
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        })

        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        review["_id"] = str(review["_id"])
        if "car_id" in review:
            review["car_id"] = str(review["car_id"])
        if "client_id" in review:
            review["client_id"] = str(review["client_id"])
        if "created_at" in review and isinstance(review["created_at"], datetime):
            review["created_at"] = review["created_at"].isoformat()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": review}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@api_router.get("/search-cars")
def search_cars(
    q: Optional[str] = Query(None),
    sort_by_price: str = Query(None, regex="^(low|high)?$"),
    sort_by_date: str = Query(None, regex="^(asce|desc)?$")
):
    try:
        
        query = {
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        }

        
        if q:
            q = q.strip()
            if re.fullmatch(r"\d{4}", q):
                query["basic_info.year"] = int(q)
            elif re.fullmatch(r"\d{5,7}", q):
                query["basic_info.price"] = {"$lte": int(q)}
            else:
                query["$or"] = [
                    {"basic_info.brand": {"$regex": q, "$options": "i"}},
                    {"basic_info.model": {"$regex": q, "$options": "i"}},
                ]

        
        sort_order = []
        if sort_by_price:
            sort_order.append(("basic_info.price", ASCENDING if sort_by_price == "low" else DESCENDING))
        if sort_by_date:
            sort_order.append(("created_at", ASCENDING if sort_by_date == "asce" else DESCENDING))

        
        if sort_order:
            cursor = car_collection.find(query).sort(sort_order)
        else:
            cursor = car_collection.find(query)

        cars = [get(car) for car in cursor]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Search results",
                "data": cars,
                "total_cars": len(cars)
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    
@api_router.get("/get-all-reviews/{car_id}")
async def get_all_reviews(car_id: str):
    try:
        query = {
            "car_id": car_id,
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        }

        cursor = review_collection.find(query)
        reviews = []
        for review in cursor:
            review["_id"] = str(review["_id"])
            review["car_id"] = str(review["car_id"])
            review["client_id"] = str(review["client_id"])
            if "created_at" in review and isinstance(review["created_at"], datetime):
             review["created_at"] = review["created_at"].isoformat()

            reviews.append(review)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": reviews}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@api_router.get("/get-cars-by-agent/{agent_id}")
def get_cars_by_agent(agent_id: str):
    try:
      
        query = {
            "agent_id": str(agent_id),
            "is_deleted": {"$ne": True},
            "status": {"$nin": ["pending", "rejected"]}
        }

        # Fetch cars from DB
        cars = list(car_collection.find(query).sort("created_at", DESCENDING))

        if not cars:
            return JSONResponse(
                status_code=404,
                content={"message": "No cars found for this agent", "data": []}
            )

        # Convert _id to string
        for car in cars:
            car["_id"] = str(car["_id"])
            car["agent_id"] = str(car["agent_id"])
            car["company_id"] = str(car["company_id"]) if "company_id" in car else None

        return JSONResponse(
            status_code=200,
            content={
                "message": "List of cars for the agent",
                "count": len(cars),
                "data": cars
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
