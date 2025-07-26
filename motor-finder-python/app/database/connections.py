from contextlib import asynccontextmanager
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient, errors
from fastapi import HTTPException
from config import DATABASE_URL

logger = logging.getLogger(__name__)
db_config = {
    "db_url": DATABASE_URL
}

async def connect():
    try:
        client = AsyncIOMotorClient(db_config["db_url"], serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client
    except errors.ConfigurationError:
        raise HTTPException(
            status_code=500, detail="Error: Invalid MongoDB configuration."
        )
    except errors.ConnectionFailure:
        raise HTTPException(
            status_code=500, detail="Error: Unable to connect to the MongoDB server."
        )
    except errors.OperationFailure as err:
        raise HTTPException(
            status_code=500, detail=f"Authentication or command error: {err}"
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")

@asynccontextmanager
async def lifespan(app):
    """Async context manager for MongoDB connection lifecycle"""
    try:
        connection = await connect()  # Await the async function
        await connection.admin.command("ping")  # MongoDB health check
        app.state.mongo_client = connection
        logger.info("✅ MongoDB connection established successfully at startup. on link ")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed at startup: {e}")
        raise

    yield  # FastAPI app runs here

    mongo_client = getattr(app.state, "mongo_client", None)
    if mongo_client:
        mongo_client.close()
        logger.info("🔌 MongoDB connection closed at shutdown.")
    logger.info("🚪 Shutting down FastAPI app.")
