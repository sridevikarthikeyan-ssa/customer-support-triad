"""
MongoDB client for batch processing.
Provides asynchronous MongoDB connectivity and operations for batch processing.
"""

import os
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from logger import logger
from utils.retry_utils import async_retry

class MongoClient:
    """
    Asynchronous MongoDB client for batch processing.
    Provides methods for connecting to MongoDB, fetching unprocessed documents,
    and storing classification results.
    """
    
    def __init__(
        self,
        mongodb_uri: str = None,
        db_name: str = None,
        source_collection: str = None,
        target_collection: str = None,
        max_pool_size: int = 20,
        min_pool_size: int = 5,
        max_idle_time_ms: int = 30000,
        connect_timeout_ms: int = 5000,
        server_selection_timeout_ms: int = 5000,
    ):
        """
        Initialize MongoDB client.
        
        Args:
            mongodb_uri: MongoDB connection URI (default: from env or standard URI)
            db_name: MongoDB database name (default: from env or "customer_support")
            source_collection: Source collection name (default: from env or "conversation_set")
            target_collection: Target collection name (default: from env or "sentimental_analysis")
            max_pool_size: Maximum connection pool size
            min_pool_size: Minimum connection pool size
            max_idle_time_ms: Maximum idle time for connections (ms)
            connect_timeout_ms: Connection timeout (ms)
            server_selection_timeout_ms: Server selection timeout (ms)
        """
        self.mongodb_uri = mongodb_uri or os.getenv("MONGODB_URI")
        self.db_name = db_name or os.getenv("MONGODB_DB", "customer_support")
        self.source_collection_name = source_collection or os.getenv(
            "MONGODB_SOURCE_COLLECTION", "conversation_set"
        )
        self.target_collection_name = target_collection or os.getenv(
            "MONGODB_TARGET_COLLECTION", "sentimental_analysis"
        )
        
        # Connection parameters
        self.connection_params = {
            "maxPoolSize": max_pool_size,
            "minPoolSize": min_pool_size,
            "maxIdleTimeMS": max_idle_time_ms,
            "connectTimeoutMS": connect_timeout_ms,
            "serverSelectionTimeoutMS": server_selection_timeout_ms,
        }
        
        self.client = None
        self.db = None
        self.source_collection = None
        self.target_collection = None
    
    async def connect(self) -> None:
        """
        Connect to MongoDB and set up collections.
        Creates indexes if they don't exist.
        """
        try:
            logger.info(f"Connecting to MongoDB: {self.mongodb_uri}")
            self.client = AsyncIOMotorClient(self.mongodb_uri, **self.connection_params)
            self.db = self.client[self.db_name]
            self.source_collection = self.db[self.source_collection_name]
            self.target_collection = self.db[self.target_collection_name]
            logger.info(f"[DEBUG] After connect: db={self.db}, source_collection={self.source_collection}, target_collection={self.target_collection}")
            # Test connection by requesting server info
            server_info = await self.client.server_info()
            logger.info(f"Connected to MongoDB version {server_info.get('version', 'unknown')}")
            # Create indexes if they don't exist
            await self._create_indexes()
            logger.info(f"Successfully connected to MongoDB and set up collections")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def _create_indexes(self) -> None:
        """Create necessary indexes for efficient querying."""
        try:
            # Source collection indexes
            await self.source_collection.create_index("status")
            await self.source_collection.create_index("conversation_number")
            await self.source_collection.create_index("last_processed_at")
            
            # Target collection indexes
            await self.target_collection.create_index("conversation_number")
            await self.target_collection.create_index("source_object_id")
            await self.target_collection.create_index("processing_metadata.batch_job_id")
            
            logger.info(f"Created MongoDB indexes for efficient querying")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    @async_retry(max_retries=3, base_delay=1.0)
    async def fetch_unprocessed_documents(
        self, 
        batch_size: int = 100, 
        last_object_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch a batch of unprocessed documents using ObjectId-based pagination.
        
        Args:
            batch_size: Maximum number of documents to fetch
            last_object_id: ObjectId to start from (for pagination)
            
        Returns:
            List of unprocessed documents
        """
        if self.source_collection is None:
            raise ValueError("Not connected to MongoDB")
        
        # Build the query filter: only fetch documents not marked as processed
        query_filter = {"status": {"$ne": "processed"}}
        # Add ObjectId pagination if provided
        if last_object_id:
            from bson.objectid import ObjectId
            query_filter["_id"] = {"$gt": ObjectId(last_object_id)}
        # Fetch documents with strict limit
        cursor = self.source_collection.find(query_filter).limit(batch_size)
        
        documents = []
        first_id = None
        last_id = None
        
        # Enforce strict batch size limit
        count = 0
        
        async for doc in cursor:
            if count >= batch_size:
                break
                
            if not first_id:
                first_id = str(doc["_id"])
            last_id = str(doc["_id"])
            documents.append(doc)
            count += 1
        
        logger.info(f"Fetched {len(documents)} unprocessed documents (batch size limit: {batch_size})")
        return documents, first_id, last_id
    
    @async_retry(max_retries=3, base_delay=1.0)
    async def update_document_status(
        self, 
        doc_id: str, 
        status: str = "processing", 
        result_id: Optional[str] = None
    ) -> None:
        """
        Update the processing status of a document in the source collection.
        
        Args:
            doc_id: Document ID to update
            status: New status value ("pending", "processing", "processed", "failed")
            result_id: ID of the result document in the target collection
        """
        if self.source_collection is None:
            raise ValueError("Not connected to MongoDB")
        
        from bson.objectid import ObjectId
        
        update_data = {
            "status": status,
            "last_processed_at": datetime.now(timezone.utc)
        }
        
        if result_id:
            update_data["result_id"] = result_id
        
        await self.source_collection.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_data, "$inc": {"processing_attempts": 1}}
        )
        
        logger.debug(f"Updated document {doc_id} status to {status}")
    
    @async_retry(max_retries=3, base_delay=1.0)
    async def store_classification_result(
        self, 
        document: Dict[str, Any], 
        classification: Dict[str, Any],
        batch_job_id: str,
        tweets: List[Dict] = None
    ) -> str:
        """
        Store classification result in the target collection.
        
        Args:
            document: Source document with the original conversation
            classification: Classification result
            batch_job_id: ID of the current batch job
            tweets: List of tweet objects from original document
            
        Returns:
            ID of the created document in the target collection
        """
        if self.target_collection is None:
            raise ValueError("Not connected to MongoDB")
        
        # Extract conversation data
        conversation_number = document.get("conversation_number", str(document.get("_id")))
        source_id = str(document.get("_id"))
        
        # Create result document
        result_doc = {
            "conversation_number": conversation_number,
            "source_object_id": source_id,
            "classification": classification,
            "messages": None,  # Set to null as per the example
            "tweets": tweets or document.get("tweets", []),  # Use provided tweets or get from document
            "processed_at": datetime.now(timezone.utc),
            "processing_metadata": {
                "batch_job_id": batch_job_id,
                "processing_attempts": document.get("processing_attempts", 0) + 1
            },
            "customer": document.get("customer")  # Added new global field, preserves all existing fields
        }
        
        # Insert into target collection
        result = await self.target_collection.insert_one(result_doc)
        result_id = str(result.inserted_id)
        
        logger.debug(f"Stored classification for document {source_id} with result_id {result_id}")
        return result_id
    
    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
            self.client = None