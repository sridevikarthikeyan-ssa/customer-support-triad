"""
Helper utilities for MongoDB integration tests.
Provides functions for setup, teardown, and test data management.
"""

import asyncio
import os
import json
from datetime import datetime, timezone
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
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
    client = AsyncIOMotorClient(MONGODB_TEST_URI, **MONGODB_TEST_PARAMS)
    db = client[MONGODB_TEST_DB]
    
    # Create collections if they don't exist (MongoDB creates them on first insert)
    # Clear any existing data
    await db[MONGODB_TEST_SOURCE_COLLECTION].delete_many({})
    await db[MONGODB_TEST_TARGET_COLLECTION].delete_many({})
    
    # Create indexes
    await db[MONGODB_TEST_SOURCE_COLLECTION].create_index("status")
    await db[MONGODB_TEST_SOURCE_COLLECTION].create_index("conversation_number")
    await db[MONGODB_TEST_SOURCE_COLLECTION].create_index("last_processed_at")
    
    await db[MONGODB_TEST_TARGET_COLLECTION].create_index("conversation_number")
    await db[MONGODB_TEST_TARGET_COLLECTION].create_index("source_object_id")
    await db[MONGODB_TEST_TARGET_COLLECTION].create_index("processing_metadata.batch_job_id")
    
    client.close()
    return True

async def teardown_test_db():
    """
    Clean up the test MongoDB collections.
    Removes all test data to leave the environment clean.
    """
    client = AsyncIOMotorClient(MONGODB_TEST_URI, **MONGODB_TEST_PARAMS)
    db = client[MONGODB_TEST_DB]
    
    # Remove all test data
    await db[MONGODB_TEST_SOURCE_COLLECTION].delete_many({})
    await db[MONGODB_TEST_TARGET_COLLECTION].delete_many({})
    
    client.close()
    return True

async def insert_test_documents(count=10, status="pending"):
    """
    Insert test documents into the source collection.
    
    Args:
        count: Number of test documents to insert
        status: Status to set for the documents ('pending', 'processing', 'processed')
        
    Returns:
        List of inserted document IDs
    """
    client = AsyncIOMotorClient(MONGODB_TEST_URI, **MONGODB_TEST_PARAMS)
    db = client[MONGODB_TEST_DB]
    
    documents = []
    for i in range(count):
        doc = {
            "conversation_number": f"TEST-CONV-{i}",
            "messages": [
                {"role": "user", "content": f"This is test message {i} from user"},
                {"role": "agent", "content": f"This is test response {i} from agent"}
            ],
            "status": status,
            "processing_attempts": 0,
            "created_at": datetime.now(timezone.utc),
            "metadata": {
                "test": True,
                "customer_id": f"test-customer-{i}",
                "source": "integration_test"
            }
        }
        documents.append(doc)
    
    result = await db[MONGODB_TEST_SOURCE_COLLECTION].insert_many(documents)
    client.close()
    
    return [str(id) for id in result.inserted_ids]

async def check_document_status(doc_id, expected_status):
    """
    Check if a document has the expected status.
    
    Args:
        doc_id: Document ID to check
        expected_status: Expected status value
        
    Returns:
        True if status matches, False otherwise
    """
    client = AsyncIOMotorClient(MONGODB_TEST_URI, **MONGODB_TEST_PARAMS)
    db = client[MONGODB_TEST_DB]
    
    doc = await db[MONGODB_TEST_SOURCE_COLLECTION].find_one({"_id": ObjectId(doc_id)})
    client.close()
    
    if doc and doc.get("status") == expected_status:
        return True
    return False

async def count_documents(collection_name, query=None):
    """
    Count documents in a collection.
    
    Args:
        collection_name: Name of the collection ('source' or 'target')
        query: Query filter to apply
        
    Returns:
        Document count
    """
    client = AsyncIOMotorClient(MONGODB_TEST_URI, **MONGODB_TEST_PARAMS)
    db = client[MONGODB_TEST_DB]
    
    if query is None:
        query = {}
        
    if collection_name == 'source':
        count = await db[MONGODB_TEST_SOURCE_COLLECTION].count_documents(query)
    elif collection_name == 'target':
        count = await db[MONGODB_TEST_TARGET_COLLECTION].count_documents(query)
    else:
        count = 0
        
    client.close()
    return count