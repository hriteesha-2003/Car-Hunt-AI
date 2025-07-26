import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel

from app.database.connections import connect

async def seed_data():
    # Connect to MongoDB (using your connection method)

    client = await connect()
    db = client["motorfinder"]
    collection = db["category"]
    
    # Clear existing data
    await collection.delete_many({})
    
    # Insert new master data
    await collection.insert_many([
        {
            "category": "bike",
            "subcategories": [
                {"id": 1, "name": "electric"},
                {"id": 2, "name": "manual"},
                {"id": 3, "name": "Petrol"}
            ]
        },
        {
            "category": "motor",
            "subcategories": [
                {"id": 1, "name": "scooter"},
                {"id": 2, "name": "sports"}
            ]
        },
        {
            "category": "car",
            "subcategories": [
                {"id": 1, "name": "sedan"},
                {"id": 2, "name": "suv"},
                {"id": 3, "name": "Volvo"}
            ]
        }
    ])
    
    # Add indexes for better performance
    await collection.create_indexes([
        IndexModel([("category", 1)], unique=True),
        IndexModel([("subcategories.id", 1)])
    ])
    
    print("Category data seeded successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
