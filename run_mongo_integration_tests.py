"""
Script to run all MongoDB integration tests directly without using pytest.
This avoids issues with event loops and provides more direct control.
"""

import asyncio
import os
import random
from datetime import datetime, timezone
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from mongo_client import MongoClient
from tests.integration_config import (
    MONGODB_TEST_URI,
    MONGODB_TEST_DB,
    MONGODB_TEST_SOURCE_COLLECTION,
    MONGODB_TEST_TARGET_COLLECTION,
    MONGODB_TEST_PARAMS,
    TEST_BATCH_SIZE
)

# Create a unique ID for this test run to avoid conflicts if multiple tests run simultaneously
TEST_RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

async def setup_test_db():
    """
    Set up the test MongoDB collections.
    Creates collections if they don't exist and clears any existing data.
    """
    print(f"Connecting to {MONGODB_TEST_URI}")
    client = AsyncIOMotorClient(MONGODB_TEST_URI, **MONGODB_TEST_PARAMS)
    db = client[MONGODB_TEST_DB]
    
    # Clear any existing data
    await db[MONGODB_TEST_SOURCE_COLLECTION].delete_many({"test_run_id": TEST_RUN_ID})
    await db[MONGODB_TEST_TARGET_COLLECTION].delete_many({"test_run_id": TEST_RUN_ID})
    
    # Create indexes
    await db[MONGODB_TEST_SOURCE_COLLECTION].create_index("status")
    await db[MONGODB_TEST_SOURCE_COLLECTION].create_index("conversation_number")
    await db[MONGODB_TEST_SOURCE_COLLECTION].create_index("test_run_id")
    await db[MONGODB_TEST_TARGET_COLLECTION].create_index("test_run_id")
    
    client.close()
    return True

async def insert_test_documents(client, count=10, status="pending"):
    """
    Insert test documents into the source collection.
    
    Args:
        client: AsyncIOMotorClient instance
        count: Number of test documents to insert
        status: Status to set for the documents ('pending', 'processing', 'processed')
        
    Returns:
        List of inserted document IDs
    """
    db = client[MONGODB_TEST_DB]
    
    documents = []
    for i in range(count):
        doc = {
            "conversation_number": f"TEST-CONV-{TEST_RUN_ID}-{i}",
            "messages": [
                {"role": "user", "content": f"This is test message {i} from user"},
                {"role": "agent", "content": f"This is test response {i} from agent"}
            ],
            "status": status,
            "processing_attempts": 0,
            "created_at": datetime.now(timezone.utc),
            "test_run_id": TEST_RUN_ID,
            "metadata": {
                "test": True,
                "customer_id": f"test-customer-{i}",
                "source": "integration_test"
            }
        }
        documents.append(doc)
    
    result = await db[MONGODB_TEST_SOURCE_COLLECTION].insert_many(documents)
    
    return [str(id) for id in result.inserted_ids]

async def teardown_test_db():
    """
    Clean up the test MongoDB collections.
    Removes all test data created by this run.
    """
    client = AsyncIOMotorClient(MONGODB_TEST_URI, **MONGODB_TEST_PARAMS)
    db = client[MONGODB_TEST_DB]
    
    # Remove all test data for this run
    await db[MONGODB_TEST_SOURCE_COLLECTION].delete_many({"test_run_id": TEST_RUN_ID})
    await db[MONGODB_TEST_TARGET_COLLECTION].delete_many({"test_run_id": TEST_RUN_ID})
    
    client.close()
    return True

async def test_connect_to_mongodb():
    """Test connecting to MongoDB and validating connection."""
    print("\n=== Running test_connect_to_mongodb ===")
    
    # Create MongoDB client
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
    await mongo_client.connect()
    
    # Test if connection was successful
    assert mongo_client.client is not None, "Client is None"
    assert mongo_client.db is not None, "DB is None"
    assert mongo_client.source_collection is not None, "Source collection is None"
    assert mongo_client.target_collection is not None, "Target collection is None"
    
    await mongo_client.close()
    print("✅ Test passed!")
    return True

async def test_fetch_unprocessed_documents():
    """Test fetching unprocessed documents from MongoDB."""
    print("\n=== Running test_fetch_unprocessed_documents ===")
    
    # Create MongoDB client
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
    await mongo_client.connect()
    
    # Insert test documents with "pending" status
    doc_ids = await insert_test_documents(mongo_client.client, count=5, status="pending")
    
    # Fetch unprocessed documents
    documents, first_id, last_id = await mongo_client.fetch_unprocessed_documents(batch_size=TEST_BATCH_SIZE)
    
    # Verify results
    assert len(documents) >= 5, f"Expected at least 5 documents, got {len(documents)}"
    assert first_id is not None, "First ID is None"
    assert last_id is not None, "Last ID is None"
    assert all(doc["status"] != "processed" for doc in documents), "Found processed documents"
    
    await mongo_client.close()
    print("✅ Test passed!")
    return True

async def test_update_document_status():
    """Test updating document status in MongoDB."""
    print("\n=== Running test_update_document_status ===")
    
    # Create MongoDB client
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
    await mongo_client.connect()
    
    # Insert a test document
    doc_ids = await insert_test_documents(mongo_client.client, count=1, status="pending")
    doc_id = doc_ids[0]
    
    # Update the document status
    await mongo_client.update_document_status(doc_id, "processing")
    
    # Verify the status was updated
    client = mongo_client.client
    db = client[MONGODB_TEST_DB]
    doc = await db[MONGODB_TEST_SOURCE_COLLECTION].find_one({"_id": ObjectId(doc_id)})
    
    assert doc["status"] == "processing", f"Expected status 'processing', got '{doc['status']}'"
    
    # Update with result ID
    result_id = "test-result-id-12345"
    await mongo_client.update_document_status(doc_id, "processed", result_id)
    
    # Get the document directly to verify the result_id
    doc = await db[MONGODB_TEST_SOURCE_COLLECTION].find_one({"_id": ObjectId(doc_id)})
    
    assert doc["status"] == "processed", f"Expected status 'processed', got '{doc['status']}'"
    assert doc["result_id"] == result_id, f"Expected result_id '{result_id}', got '{doc.get('result_id')}'"
    
    await mongo_client.close()
    print("✅ Test passed!")
    return True

async def test_store_classification_result():
    """Test storing classification results in MongoDB."""
    print("\n=== Running test_store_classification_result ===")
    
    # Create MongoDB client
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
    await mongo_client.connect()
    
    # Insert a test document
    doc_ids = await insert_test_documents(mongo_client.client, count=1, status="processing")
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
    
    batch_job_id = f"integration-test-batch-{TEST_RUN_ID}"
    
    # Create sample tweets
    tweets = [
        {
            "text": "I have a question about my bill",
            "tweet_id": "t123456",
            "author_id": "cust123",
            "role": "customer"
        }
    ]
    
    # Store the classification result
    result_id = await mongo_client.store_classification_result(doc, classification, batch_job_id, tweets)
    
    # Verify the result was stored
    result_doc = await db[MONGODB_TEST_TARGET_COLLECTION].find_one({"_id": ObjectId(result_id)})
    
    assert result_doc is not None, "Result document not found"
    assert result_doc["classification"] == classification, "Classification data doesn't match"
    assert result_doc["source_object_id"] == str(doc["_id"]), "Source object ID doesn't match"
    assert result_doc["processing_metadata"]["batch_job_id"] == batch_job_id, "Batch job ID doesn't match"
    
    await mongo_client.close()
    print("✅ Test passed!")
    return True

async def test_pagination_with_last_object_id():
    """Test pagination using last_object_id parameter."""
    print("\n=== Running test_pagination_with_last_object_id ===")
    
    # Create MongoDB client
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
    await mongo_client.connect()
    
    # Insert more test documents than our batch size
    total_docs = TEST_BATCH_SIZE * 2 + 1  # Ensure we need more than 2 pages
    doc_ids = await insert_test_documents(mongo_client.client, count=total_docs, status="pending")
    
    # Fetch the first batch
    batch1, first_id, last_id1 = await mongo_client.fetch_unprocessed_documents(batch_size=TEST_BATCH_SIZE)
    
    # Filter only documents from this test run
    batch1 = [doc for doc in batch1 if doc.get("test_run_id") == TEST_RUN_ID]
    assert len(batch1) <= TEST_BATCH_SIZE, f"Expected at most {TEST_BATCH_SIZE} documents, got {len(batch1)}"
    
    # Fetch the second batch using last_object_id from first batch
    batch2, _, last_id2 = await mongo_client.fetch_unprocessed_documents(
        batch_size=TEST_BATCH_SIZE, 
        last_object_id=last_id1
    )
    
    # Filter only documents from this test run
    batch2 = [doc for doc in batch2 if doc.get("test_run_id") == TEST_RUN_ID]
    
    # Fetch the third batch
    batch3, _, _ = await mongo_client.fetch_unprocessed_documents(
        batch_size=TEST_BATCH_SIZE, 
        last_object_id=last_id2
    )
    
    # Filter only documents from this test run
    batch3 = [doc for doc in batch3 if doc.get("test_run_id") == TEST_RUN_ID]
    
    # Make sure the batches are different
    batch1_ids = [str(doc["_id"]) for doc in batch1]
    batch2_ids = [str(doc["_id"]) for doc in batch2]
    batch3_ids = [str(doc["_id"]) for doc in batch3]
    
    # Verify no overlap between batches
    assert len(set(batch1_ids).intersection(set(batch2_ids))) == 0, "Batches 1 and 2 have overlapping IDs"
    assert len(set(batch2_ids).intersection(set(batch3_ids))) == 0, "Batches 2 and 3 have overlapping IDs"
    assert len(set(batch1_ids).intersection(set(batch3_ids))) == 0, "Batches 1 and 3 have overlapping IDs"
    
    await mongo_client.close()
    print("✅ Test passed!")
    return True

async def run_tests():
    """Run all MongoDB integration tests."""
    print(f"=== Starting MongoDB Integration Tests (Run ID: {TEST_RUN_ID}) ===")
    
    # Setup test database and collections
    await setup_test_db()
    
    try:
        # Run tests
        tests = [
            test_connect_to_mongodb,
            test_fetch_unprocessed_documents,
            test_update_document_status,
            test_store_classification_result,
            test_pagination_with_last_object_id
        ]
        
        results = []
        for test in tests:
            try:
                result = await test()
                results.append((test.__name__, result, None))
            except Exception as e:
                results.append((test.__name__, False, str(e)))
        
        # Print summary
        print("\n=== Test Results ===")
        all_passed = True
        for name, result, error in results:
            status = "✅ PASS" if result else "❌ FAIL"
            all_passed = all_passed and result
            print(f"{status} - {name}")
            if error:
                print(f"    Error: {error}")
        
        if all_passed:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed!")
    
    finally:
        # Clean up
        await teardown_test_db()

if __name__ == "__main__":
    asyncio.run(run_tests())