from app.database.db import messages_collection as collection
from bson import ObjectId
from datetime import datetime

async def save_message(data: dict) -> str:
    data.setdefault("timestamp", datetime.utcnow())
    data.setdefault("read", False)
    document = {
        "sender_id": data["sender_id"],
        "receiver_id": data["receiver_id"],
        "message": data.get("message"),      # Optional
        "file_url": data.get("file_url"),    # Optional
        "timestamp": data["timestamp"],
        "is_read": data["is_read"]
    }
    result = await collection.insert_one(data)
    return str(result.inserted_id)

async def get_chat_history(sender: str, receiver: str):
    cursor = collection.find({
        "$or": [
            {"sender": sender, "receiver": receiver},
            {"sender": receiver, "receiver": sender}
        ]
    }).sort("timestamp", 1)

    messages = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        messages.append(doc)
    return messages

async def mark_as_read(message_id: str):
    await collection.update_one(
        {"_id": ObjectId(message_id)},
        {"$set": {"read": True}}
    )
