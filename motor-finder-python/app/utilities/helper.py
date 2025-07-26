from bson import ObjectId
from fastapi import HTTPException
from app.database.db import agent_collection, car_collection

async def refresh_agent_listing(agent_id: ObjectId):
    try:
        listing_count = await car_collection.count_documents({
            "agent_id": agent_id,
            "$or": [{"is_deleted": False}, {"is_deleted": {"$exists": False}}]
        })
        await agent_collection.update_one(
            {"_id": agent_id},
            {"$set": {"listing": str(listing_count)}}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))