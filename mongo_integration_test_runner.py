"""
Simple script to run MongoDB integration tests directly.
"""

import asyncio
import os
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from mongo_client import MongoClient
from tests.integration_config import (
    MONGODB_TEST_URI,
    MONGODB_TEST_DB,
    MONGODB_TEST_SOURCE_COLLECTION,
    MONGODB_TEST_TARGET_COLLECTION,
    MONGODB_TEST_PARAMS
)

async def setup_test_db():
    """
    Set up the test MongoDB collections.
    Creates collections if they don't exist and clears any existing data.
    """
    print(f"Connecting to {MONGODB_TEST_URI}")
    client = AsyncIOMotorClient(MONGODB_TEST_URI, **MONGODB_TEST_PARAMS)
    db = client[MONGODB_TEST_DB]
    
    # Clear any existing data
    await db[MONGODB_TEST_SOURCE_COLLECTION].delete_many({})
    await db[MONGODB_TEST_TARGET_COLLECTION].delete_many({})
    
    # Create indexes
    await db[MONGODB_TEST_SOURCE_COLLECTION].create_index("status")
    await db[MONGODB_TEST_SOURCE_COLLECTION].create_index("conversation_number")
    
    client.close()
    return True

async def test_mongo_connection():
    """Test the MongoDB connection"""
    # Setup test database
    await setup_test_db()
    
    # Create MongoDB client
    print("Creating MongoClient instance")
    mongo_client = MongoClient(
        mongodb_uri=MONGODB_TEST_URI,
        db_name=MONGODB_TEST_DB,
        source_collection=MONGODB_TEST_SOURCE_COLLECTION,
        target_collection=MONGODB_TEST_TARGET_COLLECTION,
        max_pool_size=MONGODB_TEST_PARAMS["maxPoolSize"],
        min_pool_size=MONGODB_TEST_PARAMS["minPoolSize"],
        max_idle_time_ms=MONGODB_TEST_PARAMS["maxIdleTimeMS"],
        connect_timeout_ms=MONGODB_TEST_PARAMS["connectTimeoutMS"],
        server_selection_timeout_ms=MONGODB_TEST_PARAMS["serverSelectionTimeoutMS"]
    )
    
    # Connect to MongoDB
    print("Connecting to MongoDB")
    await mongo_client.connect()
    
    # Test if connection was successful
    print("Checking connection")
    assert mongo_client.client is not None
    assert mongo_client.db is not None
    assert mongo_client.source_collection is not None
    assert mongo_client.target_collection is not None
    
    print("MongoDB connection test passed!")
    
    # Clean up
    await mongo_client.close()

if __name__ == "__main__":
    asyncio.run(test_mongo_connection())