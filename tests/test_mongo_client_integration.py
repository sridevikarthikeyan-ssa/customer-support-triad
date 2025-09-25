"""
Integration tests for MongoDB client with real MongoDB connection.

These tests connect to an actual MongoDB instance and verify the 
functionality of the MongoClient class with real database operations.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta, timezone
from bson.objectid import ObjectId
import pytest_asyncio

from mongo_client import MongoClient
from tests.integration_config import (
    MONGODB_TEST_URI,
    MONGODB_TEST_DB,
    MONGODB_TEST_SOURCE_COLLECTION,
    MONGODB_TEST_TARGET_COLLECTION,
    MONGODB_TEST_PARAMS,
    TEST_BATCH_SIZE
)
from tests.integration_helpers import (
    setup_test_db, 
    teardown_test_db, 
    insert_test_documents,
    check_document_status,
    count_documents
)

# Define a shared event loop for all tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="module")
async def setup_mongodb():
    """
    Setup fixture for MongoDB integration tests.
    Creates the test environment and cleans up afterward.
    """
    # Setup test database and collections
    await setup_test_db()
    
    # Create and yield the MongoDB client
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
    
    await mongo_client.connect()
    yield mongo_client
    
    # Cleanup
    await mongo_client.close()
    await teardown_test_db()

class TestMongoClientIntegration:
    """Integration tests for MongoClient with real MongoDB."""
    
    @pytest.mark.asyncio
    async def test_connect_to_mongodb(self, setup_mongodb):
        """Test connecting to MongoDB and validating connection."""
        mongo_client = setup_mongodb
        
        # If we got here, connection was successful (the fixture connected)
        assert mongo_client.client is not None
        assert mongo_client.db is not None
        assert mongo_client.source_collection is not None
        assert mongo_client.target_collection is not None
    
    @pytest.mark.asyncio
    async def test_fetch_unprocessed_documents(self, setup_mongodb):
        """Test fetching unprocessed documents from MongoDB."""
        mongo_client = setup_mongodb
        
        # Insert test documents with "pending" status
        doc_ids = await insert_test_documents(count=5, status="pending")
        
        # Fetch unprocessed documents
        documents, first_id, last_id = await mongo_client.fetch_unprocessed_documents(batch_size=TEST_BATCH_SIZE)
        
        # Verify results
        assert len(documents) == 5
        assert first_id is not None
        assert last_id is not None
        assert all(doc["status"] != "processed" for doc in documents)
    
    @pytest.mark.asyncio
    async def test_update_document_status(self, setup_mongodb):
        """Test updating document status in MongoDB."""
        mongo_client = setup_mongodb
        
        # Insert a test document
        doc_ids = await insert_test_documents(count=1, status="pending")
        doc_id = doc_ids[0]
        
        # Update the document status
        await mongo_client.update_document_status(doc_id, "processing")
        
        # Verify the status was updated
        status_updated = await check_document_status(doc_id, "processing")
        assert status_updated is True
        
        # Update with result ID
        result_id = "test-result-id-12345"
        await mongo_client.update_document_status(doc_id, "processed", result_id)
        
        # Get the document directly to verify the result_id
        client = mongo_client.client
        db = client[MONGODB_TEST_DB]
        doc = await db[MONGODB_TEST_SOURCE_COLLECTION].find_one({"_id": ObjectId(doc_id)})
        
        assert doc["status"] == "processed"
        assert doc["result_id"] == result_id
    
    @pytest.mark.asyncio
    async def test_store_classification_result(self, setup_mongodb):
        """Test storing classification results in MongoDB."""
        mongo_client = setup_mongodb
        
        # Insert a test document
        doc_ids = await insert_test_documents(count=1, status="processing")
        doc_id = doc_ids[0]
        
        # Get the document to use for classification
        client = mongo_client.client
        db = client[MONGODB_TEST_DB]
        doc = await db[MONGODB_TEST_SOURCE_COLLECTION].find_one({"_id": ObjectId(doc_id)})
        
        # Create a classification result
        classification = {
            "intent": "inquiry",
            "topic": "billing",
            "sentiment": "neutral",
            "priority": "medium"
        }
        
        batch_job_id = "integration-test-batch-001"
        
        # Ensure we have tweets in the test document
        tweets = doc.get("tweets", [{"text": "This is a test message", "tweet_id": "test123", "author_id": "test_user"}])
        
        # Store the classification result
        result_id = await mongo_client.store_classification_result(doc, classification, batch_job_id, tweets)
        
        # Verify the result was stored
        result_doc = await db[MONGODB_TEST_TARGET_COLLECTION].find_one({"_id": ObjectId(result_id)})
        
        assert result_doc is not None
        assert result_doc["classification"] == classification
        assert result_doc["source_object_id"] == str(doc["_id"])
        assert result_doc["processing_metadata"]["batch_job_id"] == batch_job_id
    
    @pytest.mark.asyncio
    async def test_pagination_with_last_object_id(self, setup_mongodb):
        """Test pagination using last_object_id parameter."""
        mongo_client = setup_mongodb
        
        # Insert more test documents than our batch size
        total_docs = TEST_BATCH_SIZE * 2 + 1  # Ensure we need more than 2 pages
        doc_ids = await insert_test_documents(count=total_docs, status="pending")
        
        # Fetch the first batch
        batch1, first_id, last_id1 = await mongo_client.fetch_unprocessed_documents(batch_size=TEST_BATCH_SIZE)
        assert len(batch1) == TEST_BATCH_SIZE
        
        # Fetch the second batch using last_object_id from first batch
        batch2, _, last_id2 = await mongo_client.fetch_unprocessed_documents(
            batch_size=TEST_BATCH_SIZE, 
            last_object_id=last_id1
        )
        assert len(batch2) == TEST_BATCH_SIZE
        
        # Fetch the third batch (should have just one document)
        batch3, _, _ = await mongo_client.fetch_unprocessed_documents(
            batch_size=TEST_BATCH_SIZE, 
            last_object_id=last_id2
        )
        assert len(batch3) == 1
        
        # Make sure the batches are different
        batch1_ids = [str(doc["_id"]) for doc in batch1]
        batch2_ids = [str(doc["_id"]) for doc in batch2]
        batch3_ids = [str(doc["_id"]) for doc in batch3]
        
        # Verify no overlap between batches
        assert not set(batch1_ids).intersection(set(batch2_ids))
        assert not set(batch2_ids).intersection(set(batch3_ids))
        assert not set(batch1_ids).intersection(set(batch3_ids))
        
        # Verify we got all documents
        assert len(batch1) + len(batch2) + len(batch3) == total_docs