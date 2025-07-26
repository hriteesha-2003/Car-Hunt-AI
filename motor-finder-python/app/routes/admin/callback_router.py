import datetime
import json
import random
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from app.database.connections import connect 

callback_router = APIRouter(tags=["Callback"])
logger = logging.getLogger(__name__)

@callback_router.post("/callback")
async def handle_callback(request: Request):
    try:
        # Parse request data
        try:
            request_data = await request.json()
        except json.JSONDecodeError:
            request_data = {}
            logger.warning("No valid JSON received, using dummy data")

        # Prepare default data
        default_data = {
            "name": f"User_{random.randint(1000, 9999)}",
            "email": f"user_{random.randint(1000, 9999)}@example.com",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "dummy": True
        }

        # Merge with incoming data
        data = {**default_data, **request_data}

        try:
            # Connect to MongoDB and select the database
            client = await connect()
            db = client["motorfinder"]  # Replace with your actual DB name if not using config

            # Insert document into "callbacks" collection
            result = await db.callbacks.insert_one(data)
            data["_id"] = str(result.inserted_id)

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Callback data stored successfully",
                    "data": data
                }
            )

        except HTTPException as db_err:
            logger.error(f"Database operation failed: {db_err.detail}")
            raise
        except Exception as db_ops_err:
            logger.error(f"Database operation error: {str(db_ops_err)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database operation failed: {str(db_ops_err)}"
            )

    except Exception as e:
        logger.error(f"Unexpected error in callback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    
# @callback_router.post("/callback")
# async def handle_callback(request: Request):
#     try:
#         data = await request.json()
#         if not data:
#             raise HTTPException(status_code=400,detail="No data received in callback")
#         db = await connect()
#         result = await db.callbacks.insert_one(data)
#         data["_id"] = str(result.inserted_id)
        
#         return JSONResponse(
#             status_code=200,
#             content={
#                 "message": "Callback data stored successfully",
#                 "data": data
#             }
#         )
#     except json.JSONDecodeError:
#         raise HTTPException(status_code=400,detail="Invalid JSON data received")
#     except Exception as e:
#         raise HTTPException(status_code=500,detail=f"Error processing callback: {str(e)}")
