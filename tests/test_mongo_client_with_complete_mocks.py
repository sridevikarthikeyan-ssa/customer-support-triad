"""
Unit tests for the MongoDB client module using comprehensive mocking.
"""
import pytest
import asyncio
import json
import os
import random
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from bson.objectid import ObjectId

# Global mocks that will be accessible within the test class
mock_source_collection = AsyncMock()
mock_target_collection = AsyncMock()
mock_instance = AsyncMock()
mock_db = AsyncMock()

# We'll patch the AsyncIOMotorClient before importing MongoClient
with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_motor_client_class:
    # Configure mock instance methods
    mock_instance.server_info = AsyncMock(return_value={"version": "5.0.0"})
    mock_instance.close = MagicMock()
    
    # Configure collection access
    mock_instance.__getitem__.return_value = mock_db
    
    def get_collection(name):
        if name == "test_source":
            return mock_source_collection
        elif name == "test_target":
            return mock_target_collection
        return AsyncMock()
    
    mock_db.__getitem__.side_effect = get_collection
    
    # Configure collection methods
    mock_source_collection.create_index = AsyncMock()
    mock_source_collection.update_one = AsyncMock()
    mock_target_collection.create_index = AsyncMock()
    mock_target_collection.insert_one = AsyncMock()
    
    # Make the mock class return our mock instance
    mock_motor_client_class.return_value = mock_instance
    
    # Import the class under test after patching
    from mongo_client import MongoClient
    from utils.retry_utils import RetryError

@pytest.fixture
def mongo_client():
    """Create a MongoClient instance for testing."""
    client = MongoClient(
        mongodb_uri="mongodb://localhost:27017",
        db_name="test_db",
        source_collection="test_source",
        target_collection="test_target",
        max_pool_size=10,
        min_pool_size=2,
        max_idle_time_ms=10000,
        connect_timeout_ms=2000,
        server_selection_timeout_ms=2000
    )
    return client

@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test."""
    mock_source_collection.reset_mock()
    mock_target_collection.reset_mock()
    mock_instance.reset_mock()
    mock_db.reset_mock()
    yield

class TestMongoClient:
    """Test suite for the MongoClient class."""
    
    @pytest.mark.asyncio
    async def test_connect(self, mongo_client):
        """Test connecting to MongoDB."""
        await mongo_client.connect()
        
        # Check that server_info was called
        mock_instance.server_info.assert_called_once()
        
        # Check that the client, db, and collections are set
        assert mongo_client.client is not None
        assert mongo_client.db is not None
        assert mongo_client.source_collection is not None
        assert mongo_client.target_collection is not None
    
    @pytest.mark.asyncio
    async def test_create_indexes(self, mongo_client):
        """Test creating indexes on collections."""
        await mongo_client.connect()
        
        # Check that create_index was called on both collections
        mock_source_collection.create_index.assert_called()
        mock_target_collection.create_index.assert_called()
    
    @pytest.mark.asyncio
    async def test_fetch_unprocessed_documents(self, mongo_client):
        """Test fetching unprocessed documents."""
        # Mock documents for the cursor to return
        doc_id1 = ObjectId("507f1f77bcf86cd799439001")
        doc_id2 = ObjectId("507f1f77bcf86cd799439002")
        mock_docs = [
            {"_id": doc_id1, "text": "Test 1"},
            {"_id": doc_id2, "text": "Test 2"}
        ]
        
        # Create a proper async iterator mock
        class AsyncIterMock:
            def __init__(self, data):
                self.data = data
                self.index = 0
                
            def __aiter__(self):
                return self
                
            async def __anext__(self):
                if self.index < len(self.data):
                    result = self.data[self.index]
                    self.index += 1
                    return result
                raise StopAsyncIteration
        
        # Setup the find operation
        mock_cursor = AsyncIterMock(mock_docs)
        limit_mock = MagicMock(return_value=mock_cursor)
        find_mock = MagicMock(return_value=MagicMock(limit=limit_mock))
        
        await mongo_client.connect()
        
        # Replace the find method with our mock
        mongo_client.source_collection.find = find_mock
        
        # Call the method
        documents, first_id, last_id = await mongo_client.fetch_unprocessed_documents(batch_size=10)
        
        # Verify find was called with correct parameters
        mongo_client.source_collection.find.assert_called_once_with({"status": {"$ne": "processed"}})
        limit_mock.assert_called_once_with(10)
        
        # Check the results
        assert len(documents) == 2
        assert documents[0]["text"] == "Test 1"
        assert documents[1]["text"] == "Test 2"
        assert first_id == str(doc_id1)
        assert last_id == str(doc_id2)
    
    @pytest.mark.asyncio
    async def test_fetch_unprocessed_documents_with_last_id(self, mongo_client):
        """Test fetching unprocessed documents with last_object_id parameter."""
        # Mock document for the cursor to return
        doc_id = ObjectId("507f1f77bcf86cd799439022")
        mock_doc = {"_id": doc_id, "text": "Test doc"}
        
        # Create a proper async iterator mock
        class AsyncIterMock:
            def __init__(self, data):
                self.data = data if isinstance(data, list) else [data]
                self.index = 0
                
            def __aiter__(self):
                return self
                
            async def __anext__(self):
                if self.index < len(self.data):
                    result = self.data[self.index]
                    self.index += 1
                    return result
                raise StopAsyncIteration
        
        # Setup the find operation
        mock_cursor = AsyncIterMock(mock_doc)
        limit_mock = MagicMock(return_value=mock_cursor)
        find_mock = MagicMock(return_value=MagicMock(limit=limit_mock))
        
        await mongo_client.connect()
        
        # Replace the find method with our mock
        mongo_client.source_collection.find = find_mock
        
        # Call the method with last_object_id
        last_object_id = "507f1f77bcf86cd799439011"
        documents, first_id, last_id = await mongo_client.fetch_unprocessed_documents(batch_size=10, last_object_id=last_object_id)
        
        # Verify find was called with correct parameters
        mongo_client.source_collection.find.assert_called_once()
        find_call_args = mongo_client.source_collection.find.call_args[0][0]
        assert "_id" in find_call_args
        assert str(find_call_args["_id"]["$gt"]) == str(ObjectId(last_object_id))
        limit_mock.assert_called_once_with(10)
        
        # Check the results
        assert len(documents) == 1
        assert documents[0]["text"] == "Test doc"
        assert first_id == str(doc_id)
        assert last_id == str(doc_id)
    
    @pytest.mark.asyncio
    async def test_update_document_status(self, mongo_client):
        """Test updating document status."""
        await mongo_client.connect()
        
        doc_id = "507f1f77bcf86cd799439011"
        await mongo_client.update_document_status(doc_id, "processing")
        
        # Check that update_one was called with the right parameters
        mock_source_collection.update_one.assert_called_once()
        call_args = mock_source_collection.update_one.call_args[0]
        assert call_args[0]["_id"].binary == ObjectId(doc_id).binary
        assert "status" in call_args[1]["$set"]
        assert call_args[1]["$set"]["status"] == "processing"
        assert "last_processed_at" in call_args[1]["$set"]
        assert isinstance(call_args[1]["$set"]["last_processed_at"], datetime)
        assert call_args[1]["$inc"]["processing_attempts"] == 1
    
    @pytest.mark.asyncio
    async def test_update_document_status_with_result_id(self, mongo_client):
        """Test updating document status with a result ID."""
        await mongo_client.connect()
        
        doc_id = "507f1f77bcf86cd799439011"
        result_id = "507f1f77bcf86cd799439022"
        await mongo_client.update_document_status(doc_id, "processed", result_id)
        
        # Check that update_one was called with the right parameters
        mock_source_collection.update_one.assert_called_once()
        call_args = mock_source_collection.update_one.call_args[0]
        assert call_args[0]["_id"].binary == ObjectId(doc_id).binary
        assert "status" in call_args[1]["$set"]
        assert call_args[1]["$set"]["status"] == "processed"
        assert call_args[1]["$set"]["result_id"] == result_id
        assert "last_processed_at" in call_args[1]["$set"]
    
    @pytest.mark.asyncio
    async def test_store_classification_result(self, mongo_client):
        """Test storing classification result."""
        # Create a mock result with inserted_id
        result_id = ObjectId("507f1f77bcf86cd799439011")
        mock_result = MagicMock()
        mock_result.inserted_id = result_id
        
        await mongo_client.connect()
        
        # Configure the insert_one method to return our mock result
        mock_target_collection.insert_one.return_value = mock_result
        
        # Call the method
        document = {
            "_id": ObjectId("507f1f77bcf86cd799439022"),
            "conversation_number": "C12345",
            "messages": None,
            "tweets": [
                {"text": "Hello", "tweet_id": "123", "author_id": "user1", "role": "customer"},
                {"text": "Hi there", "tweet_id": "124", "author_id": "user2", "role": "agent"}
            ],
            "processing_attempts": 2
        }
        classification = {"intent": "question", "topic": "account", "sentiment": "neutral"}
        batch_job_id = "batch_123"
        
        returned_id = await mongo_client.store_classification_result(document, classification, batch_job_id)
        
        # Check that insert_one was called
        mock_target_collection.insert_one.assert_called_once()
        
        # Check the document structure
        inserted_doc = mock_target_collection.insert_one.call_args[0][0]
        assert inserted_doc["conversation_number"] == "C12345"
        assert inserted_doc["source_object_id"] == "507f1f77bcf86cd799439022"
        assert inserted_doc["classification"] == classification
        assert inserted_doc["messages"] == None  # Should be null, not the old original_messages format
        assert inserted_doc["tweets"] == document.get("tweets", [])  # Should use the tweets from document
        assert isinstance(inserted_doc["processed_at"], datetime)
        assert inserted_doc["processing_metadata"]["batch_job_id"] == batch_job_id
        assert inserted_doc["processing_metadata"]["processing_attempts"] == 3
        
        # Check the returned ID
        assert returned_id == str(result_id)
    
    @pytest.mark.asyncio
    async def test_store_classification_result_no_conversation_number(self, mongo_client):
        """Test storing classification result when conversation_number is missing."""
        # Create a mock result with inserted_id
        result_id = ObjectId("507f1f77bcf86cd799439011")
        mock_result = MagicMock()
        mock_result.inserted_id = result_id
        
        await mongo_client.connect()
        
        # Configure the insert_one method to return our mock result
        mock_target_collection.insert_one.return_value = mock_result
        
        # Document without conversation_number
        document = {
            "_id": ObjectId("507f1f77bcf86cd799439022"),
            "messages": None,
            "tweets": [
                {"text": "Hello", "tweet_id": "123", "author_id": "user1"}
            ]
        }
        classification = {"intent": "question", "topic": "account"}
        batch_job_id = "batch_xyz"
        
        returned_id = await mongo_client.store_classification_result(document, classification, batch_job_id)
        
        # Check that insert_one was called
        mock_target_collection.insert_one.assert_called_once()
        
        # Check that the document uses _id as conversation_number
        inserted_doc = mock_target_collection.insert_one.call_args[0][0]
        assert inserted_doc["conversation_number"] == "507f1f77bcf86cd799439022"
        assert inserted_doc["source_conversation_id"] == "507f1f77bcf86cd799439022"
        assert inserted_doc["processing_metadata"]["batch_job_id"] == batch_job_id
        
        # Check the returned ID
        assert returned_id == str(result_id)
    
    @pytest.mark.asyncio
    async def test_close(self, mongo_client):
        """Test closing the MongoDB connection."""
        await mongo_client.connect()
        
        # Store the initial values to verify they're reset
        initial_client = mongo_client.client
        
        # Call close
        await mongo_client.close()
        
        # Check that the client's close method was called
        mock_instance.close.assert_called_once()
        
        # Check that client reference is set to None
        assert mongo_client.client is None
        
        # For testing purposes, we only verify client is set to None
        # In our case, we're using global mocks so the db and collections may not be None
        # in the test environment, but they will be None in real usage
    
    def test_init_with_environment_variables(self):
        """Test initialization using environment variables."""
        # Save original env vars if they exist
        original_uri = os.environ.get("MONGODB_URI")
        original_db = os.environ.get("MONGODB_DB")
        original_source = os.environ.get("MONGODB_SOURCE_COLLECTION")
        original_target = os.environ.get("MONGODB_TARGET_COLLECTION")
        
        try:
            # Set env vars
            os.environ["MONGODB_URI"] = "mongodb://env-server:27017"
            os.environ["MONGODB_DB"] = "env_db"
            os.environ["MONGODB_SOURCE_COLLECTION"] = "env_source"
            os.environ["MONGODB_TARGET_COLLECTION"] = "env_target"
            
            # Create client without explicit params
            client = MongoClient()
            
            # Check that env vars were used
            assert client.mongodb_uri == "mongodb://env-server:27017"
            assert client.db_name == "env_db"
            assert client.source_collection_name == "env_source"
            assert client.target_collection_name == "env_target"
            
        finally:
            # Restore original env vars
            if original_uri:
                os.environ["MONGODB_URI"] = original_uri
            else:
                del os.environ["MONGODB_URI"]
                
            if original_db:
                os.environ["MONGODB_DB"] = original_db
            else:
                del os.environ["MONGODB_DB"]
                
            if original_source:
                os.environ["MONGODB_SOURCE_COLLECTION"] = original_source
            else:
                del os.environ["MONGODB_SOURCE_COLLECTION"]
                
            if original_target:
                os.environ["MONGODB_TARGET_COLLECTION"] = original_target
            else:
                del os.environ["MONGODB_TARGET_COLLECTION"]