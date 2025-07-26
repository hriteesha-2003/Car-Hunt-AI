import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel
# from app.database.connections import connect

async def seed_vehicle_types():
    client = db url
    # client = await connect()
    db = client["motorfinder"]
    collection = db["vehicle_type"]
    
    # Clear existing data
    await collection.delete_many({})
    
    # Insert types like buy, sell, rent
    await collection.insert_many([
        {"type": "buy"},
        {"type": "sell"},
        {"type": "rent"}
    ])
    
    # Create a unique index on "type"
    await collection.create_indexes([
        IndexModel([("type", 1)], unique=True)
    ])
    
    print("Vehicle types (buy, sell, rent) seeded successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_vehicle_types())
