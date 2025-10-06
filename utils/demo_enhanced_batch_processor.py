"""
Demo script for the enhanced batch processor with retry logic, batch file management, 
and MongoDB cursor pagination.

This script demonstrates the advanced features of the batch processor:
1. Checkpoint-based recovery
2. Cursor-based pagination
3. Retry logic with exponential backoff
4. Local batch file management
5. Continuous monitoring mode

Usage:
    python demo_enhanced_batch_processor.py --mode batch|continuous --recover
"""
import os
import sys
import asyncio
import argparse
import json
from datetime import datetime
import logging

# Add parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from batch_processor import BatchProcessor
import mongomock_motor
from motor.motor_asyncio import AsyncIOMotorClient


class MockMongoClient:
    """Mock MongoDB client for demo purposes."""
    
    def __init__(self, use_real_mongo=False, mongodb_uri=None):
        """Initialize the mock MongoDB client."""
        self.use_real_mongo = use_real_mongo
        self.mongodb_uri = mongodb_uri
        self.client = None
        self.db = None
        self.source_collection = None
        self.target_collection = None
        self.processed_ids = set()
        
        # Sample data for testing
        self.sample_data = []
        self._generate_sample_data()
    
    def _generate_sample_data(self):
        """Generate sample data for testing."""
        customer_queries = [
            "I can't log into my account. I've tried resetting my password multiple times.",
            "Your product is amazing! I love how easy it is to use.",
            "I need to cancel my subscription immediately.",
            "How do I download my purchase history for tax purposes?",
            "This is the worst customer service I've ever experienced!",
            "I'm considering upgrading my plan, but I'm not sure which one to choose.",
            "My order was delivered late and some items were missing.",
            "Thank you so much for your help yesterday. You solved my problem perfectly!",
            "I'm getting an error message when trying to check out.",
            "Do you offer student discounts?",
            "I'd like to return this product. It doesn't work as advertised.",
            "What are your business hours?",
            "I've been waiting for a response for over a week now!",
            "How can I change my shipping address for future orders?",
            "Your app keeps crashing whenever I try to upload photos."
        ]
        
        for i, query in enumerate(customer_queries):
            self.sample_data.append({
                "_id": f"doc_{i+1}",
                "query": query,
                "timestamp": datetime.now().isoformat()
            })
            
    async def connect(self):
        """Connect to MongoDB (real or mock)."""
        try:
            if self.use_real_mongo and self.mongodb_uri:
                # Use real MongoDB connection
                self.client = AsyncIOMotorClient(self.mongodb_uri)
            else:
                # Use mongomock for testing
                self.client = mongomock_motor.AsyncMongoMockClient()
                
            self.db = self.client["customer_support_triad_demo"]
            self.source_collection = self.db["conversation_set"]
            self.target_collection = self.db["sentimental_analysis"]
            
            # Insert sample data if using mock
            if not self.use_real_mongo:
                await self._setup_mock_data()
                
            return True
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            return False
    
    async def _setup_mock_data(self):
        """Set up sample data for the mock database."""
        # Clear collections first
        await self.db["conversation_set"].delete_many({})
        await self.db["sentimental_analysis"].delete_many({})
        
        # Insert sample data
        if self.sample_data:
            await self.source_collection.insert_many(self.sample_data)
            logging.info(f"Inserted {len(self.sample_data)} documents into mock database")
    
    async def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logging.info("MongoDB connection closed")
    
    async def get_unprocessed_documents(self, batch_size=10, last_id=None):
        """
        Get unprocessed documents with cursor-based pagination.
        
        Args:
            batch_size: Number of documents to fetch
            last_id: Last processed ID for pagination
            
        Returns:
            Tuple[List, bool, str]: Documents, flag for more available, and last ID
        """
        try:
            # Build query with cursor pagination
            query = {}
            if last_id:
                query["_id"] = {"$gt": last_id}
                
            # Add filter for unprocessed documents
            query["processed"] = {"$ne": True}
            
            # Create cursor
            cursor = self.source_collection.find(
                query,
                {"_id": 1, "query": 1, "timestamp": 1}
            ).sort("_id", 1).limit(batch_size + 1)  # +1 to check if more are available
            
            # Fetch documents
            documents = await cursor.to_list(length=batch_size + 1)
            
            # Check if more documents are available
            more_available = len(documents) > batch_size
            if more_available:
                documents = documents[:batch_size]
                
            # Get the last ID for pagination
            last_id = documents[-1]["_id"] if documents else None
            
            # Remove already processed IDs (for demo purposes)
            documents = [doc for doc in documents if doc["_id"] not in self.processed_ids]
            
            return documents, more_available, last_id
            
        except Exception as e:
            logging.error(f"Error fetching unprocessed documents: {str(e)}")
            return [], False, None
    
    async def store_classification(self, classification):
        """Store classification result."""
        try:
            await self.target_collection.insert_one(classification)
            logging.info(f"Classification stored for document {classification['document_id']}")
            return True
        except Exception as e:
            logging.error(f"Error storing classification: {str(e)}")
            return False
    
    async def mark_as_processed(self, doc_id, update_data):
        """Mark a document as processed."""
        try:
            await self.source_collection.update_one(
                {"_id": doc_id},
                {"$set": update_data}
            )
            self.processed_ids.add(doc_id)  # For demo purposes
            logging.info(f"Document {doc_id} marked as processed")
            return True
        except Exception as e:
            logging.error(f"Error marking document as processed: {str(e)}")
            return False


async def demo_enhanced_batch_processor(args):
    """Run the enhanced batch processor demo."""
    # Configure the batch processor with all options
    processor = BatchProcessor(
        batch_size=args.batch_size,
        max_concurrent=args.concurrent,
        batch_dir=args.batch_dir,
        checkpoint_interval=args.checkpoint_interval,
        mode=args.mode,
        continuous_interval=args.interval,
        max_retries=args.retries
    )
    
    # Replace the MongoClient creation with our mock
    processor.mongo_client = MockMongoClient(
        use_real_mongo=args.use_real_mongo,
        mongodb_uri=args.mongodb_uri
    )
    
    # Connect to MongoDB (real or mock)
    connected = await processor.mongo_client.connect()
    if not connected:
        print("Failed to connect to MongoDB")
        return
    
    print(f"Running batch processor in {args.mode} mode...")
    if args.recover:
        print("Attempting to recover from previous checkpoint...")
        
    try:
        # Run the processor
        stats = await processor.run(
            continuous=args.mode == "continuous",
            recover=args.recover
        )
        
        # Print results
        print("\nBatch processing completed")
        print(json.dumps(stats, indent=2, default=str))
        
    except KeyboardInterrupt:
        print("\nBatch processor interrupted, saving checkpoint...")
        await processor.save_checkpoint()
        
    finally:
        if processor.mongo_client:
            await processor.mongo_client.close()


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(description="Demo for enhanced batch processor")
    
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size")
    parser.add_argument("--concurrent", type=int, default=3, help="Max concurrent LLM calls")
    parser.add_argument("--mode", choices=["batch", "continuous"], default="batch",
                       help="Processing mode: batch (one-time) or continuous (polling)")
    parser.add_argument("--interval", type=int, default=10, 
                       help="Polling interval for continuous mode (seconds)")
    parser.add_argument("--batch-dir", default="demo_batch_files", 
                       help="Directory for batch files and checkpoints")
    parser.add_argument("--checkpoint-interval", type=int, default=5,
                       help="Number of documents to process before checkpointing")
    parser.add_argument("--recover", action="store_true",
                       help="Recover from previous checkpoint")
    parser.add_argument("--retries", type=int, default=2,
                       help="Maximum number of retries for failed operations")
    parser.add_argument("--use-real-mongo", action="store_true",
                       help="Use real MongoDB connection instead of mock")
    parser.add_argument("--mongodb-uri", default=None,
                       help="MongoDB connection URI for real MongoDB")
    
    args = parser.parse_args()
    
    # Create batch directory if it doesn't exist
    os.makedirs(args.batch_dir, exist_ok=True)
    
    asyncio.run(demo_enhanced_batch_processor(args))


if __name__ == "__main__":
    main()