"""
Demo script for the batch processor.

This script creates a simulated MongoDB environment using mongomock_motor,
populates it with sample customer support queries, and processes them
using the batch processor.
"""
import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import modules
parent_dir = str(Path(__file__).parent.parent.absolute())
sys.path.append(parent_dir)

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from batch_processor import BatchProcessor
    from logger import logger
except ImportError:
    print("Required packages not found. Install using:")
    print("pip install motor")
    sys.exit(1)

# Try to import mongomock_motor, which is required for the demo
try:
    import mongomock_motor
except ImportError:
    print("mongomock_motor not found. Install using:")
    print("pip install mongomock-motor")
    sys.exit(1)


class MockBatchProcessor(BatchProcessor):
    """
    A modified version of BatchProcessor that uses mongomock_motor
    for testing without a real MongoDB connection.
    """
    
    async def connect(self, db_name: str = "customer_support_triad"):
        """
        Connect to a mock MongoDB instance and populate it with sample data.
        
        Args:
            db_name: Name of the mock database
            
        Returns:
            bool: True if connection and setup successful
        """
        try:
            logger.info("Connecting to mock MongoDB")
            self.client = mongomock_motor.AsyncMongoMockClient()
            self.db = self.client[db_name]
            self.source_collection = self.db[self.source_collection_name]
            self.target_collection = self.db[self.target_collection_name]
            
            # Populate with sample data
            await self._populate_sample_data()
            
            logger.info("Successfully connected to mock MongoDB and populated sample data")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up mock MongoDB: {str(e)}")
            return False
    
    async def _process_document(self, document: dict, semaphore: asyncio.Semaphore) -> bool:
        """
        Override the _process_document method to use mock LLM responses.
        
        Args:
            document: The document to process
            semaphore: The semaphore for concurrency control
            
        Returns:
            bool: True if processing was successful
        """
        async with semaphore:
            try:
                doc_id = document["_id"]
                query = document.get("query", "")
                
                if not query:
                    logger.warning(f"Document {doc_id} has no query field")
                    await self._mark_as_processed(doc_id, {"error": "No query field"})
                    return False
                
                logger.info(f"Processing query: {query[:100]}...")
                
                # Instead of calling LLM, generate a mock classification
                # based on the content of the query
                classification = self._generate_mock_classification(query)
                
                # Add required fields to the classification result
                classification_result = {
                    "document_id": doc_id,
                    "query": query,
                    "intent": classification.get("intent", ""),
                    "topic": classification.get("topic", ""),
                    "sentiment": classification.get("sentiment", ""),
                    "processed_at": datetime.utcnow()
                }
                
                # Store the classification result
                await self._store_classification(classification_result)
                
                # Mark the source document as processed
                await self._mark_as_processed(doc_id, {"status": "processed"})
                
                return True
                
            except Exception as e:
                logger.error(f"Error processing document {document.get('_id', 'unknown')}: {str(e)}")
                await self._mark_as_processed(document.get("_id"), {"error": str(e)})
                return False
    
    def _generate_mock_classification(self, query: str) -> dict:
        """
        Generate a mock classification based on the content of the query.
        
        Args:
            query: The query to classify
            
        Returns:
            dict: The mock classification
        """
        query = query.lower()
        
        # Default classification
        classification = {
            "intent": "general_inquiry",
            "topic": "general",
            "sentiment": "neutral"
        }
        
        # Determine intent
        if any(word in query for word in ["can't", "unable", "problem", "issue", "error", "broken", "fix"]):
            classification["intent"] = "troubleshooting"
        elif any(word in query for word in ["how", "what", "when", "where", "why"]):
            classification["intent"] = "information_request"
        elif any(word in query for word in ["return", "cancel", "refund"]):
            classification["intent"] = "return_request"
        elif any(word in query for word in ["upgrade", "premium", "subscribe"]):
            classification["intent"] = "upgrade_request"
        elif any(word in query for word in ["thank", "appreciate", "great", "excellent"]):
            classification["intent"] = "feedback_positive"
        
        # Determine topic
        if any(word in query for word in ["account", "login", "password", "sign"]):
            classification["topic"] = "account_access"
        elif any(word in query for word in ["order", "purchase", "buy", "payment"]):
            classification["topic"] = "orders_and_payments"
        elif any(word in query for word in ["shipping", "delivery", "address"]):
            classification["topic"] = "shipping_delivery"
        elif any(word in query for word in ["app", "website", "page", "checkout"]):
            classification["topic"] = "website_functionality"
        elif any(word in query for word in ["subscription", "plan", "upgrade"]):
            classification["topic"] = "subscription_management"
        
        # Determine sentiment
        if any(word in query for word in ["thank", "appreciate", "great", "excellent", "good"]):
            classification["sentiment"] = "positive"
        elif any(word in query for word in ["terrible", "awful", "bad", "unhappy", "disappointed", "angry"]):
            classification["sentiment"] = "negative"
        
        return classification
    
    async def _populate_sample_data(self):
        """
        Populate the mock MongoDB with sample customer support queries.
        """
        sample_queries = [
            "I can't log into my account after the recent update.",
            "I want to return my recent purchase. It arrived damaged.",
            "How do I change my shipping address for my subscription?",
            "Your customer service is terrible. I've been waiting for a response for days!",
            "When will the new features you promised be available?",
            "Thank you for your prompt response and resolution to my issue.",
            "The app keeps crashing when I try to make a payment.",
            "I'd like to upgrade my subscription to the premium plan.",
            "Can you help me understand how the loyalty points system works?",
            "I found a bug in your website. The checkout page doesn't load correctly."
        ]
        
        documents = []
        for i, query in enumerate(sample_queries):
            documents.append({
                "_id": f"doc{i}",
                "query": query,
                "timestamp": datetime.utcnow(),
                "source": "demo_script"
                # No 'processed' field, so it will be picked up by the processor
            })
        
        # Insert the sample data
        if documents:
            await self.source_collection.insert_many(documents)
            logger.info(f"Inserted {len(documents)} sample documents")
            
            # Display sample queries
            print("\nSample Customer Support Queries:")
            for i, doc in enumerate(documents):
                print(f"{i+1}. {doc['query']}")


async def view_results(target_collection):
    """
    View the classification results from the target collection.
    
    Args:
        target_collection: MongoDB collection with results
    """
    results = await target_collection.find().to_list(length=100)
    
    print(f"\nFound {len(results)} classification results:")
    
    for i, result in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        print(f"Query: {result['query']}")
        print(f"Intent: {result.get('intent', 'N/A')}")
        print(f"Topic: {result.get('topic', 'N/A')}")
        print(f"Sentiment: {result.get('sentiment', 'N/A')}")
        print(f"Processed at: {result['processed_at']}")


async def run_demo(batch_size=5, max_concurrent=3):
    """
    Run the batch processor demo.
    
    Args:
        batch_size: Number of documents to process in each batch
        max_concurrent: Maximum number of concurrent LLM calls
    """
    print("\n=== Batch Processor Demo ===")
    print(f"Using batch size: {batch_size}, max concurrent: {max_concurrent}")
    
    # Create the mock batch processor
    processor = MockBatchProcessor(
        batch_size=batch_size,
        max_concurrent=max_concurrent
    )
    
    try:
        # Run the processor
        print("\nRunning batch processor...")
        stats = await processor.run()
        
        print("\nProcessing Statistics:")
        print(json.dumps(stats, indent=2, default=str))
        
        # Show the classification results
        await view_results(processor.target_collection)
        
    except Exception as e:
        print(f"\nError during demo: {str(e)}")
    
    finally:
        # Close the connection
        await processor.close()
        print("\nDemo completed")


def main():
    """Command-line entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch processor demo")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size (default: 5)")
    parser.add_argument("--concurrent", type=int, default=3, help="Max concurrent LLM calls (default: 3)")
    
    args = parser.parse_args()
    
    asyncio.run(run_demo(
        batch_size=args.batch_size,
        max_concurrent=args.concurrent
    ))


if __name__ == "__main__":
    main()