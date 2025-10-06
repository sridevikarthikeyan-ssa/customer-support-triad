"""
batch_processor.py
Processes customer support queries in batches for efficient classification.

This module:
1. Connects to MongoDB collections
2. Fetches unprocessed customer queries in batches
3. Processes them concurrently using the async LLM wrapper
4. Updates MongoDB with the classification results
5. Provides crash recovery and progress tracking
"""
import os
from dotenv import load_dotenv
import asyncio
import json
from prompt_builder import build_prompt  # Import the existing prompt builder
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import time
import uuid
from logger import logger
from async_llm_wrapper import safe_ollama_classify_async
from error_handler import error_response
from mongo_client import MongoClient
from utils.batch_file_manager import BatchFileManager
from utils.retry_utils import async_retry, RetryError


load_dotenv()

class BatchProcessor:
    async def _store_classification(self, output_doc: Dict[str, Any]) -> bool:
        """Store the classified output document in the target collection."""
        try:
            await self.mongo_client.target_collection.insert_one(output_doc)
            logger.info(f"Stored classified document with _id={output_doc.get('_id')}")
            return True
        except Exception as e:
            logger.error(f"Error storing classified document: {str(e)}")
            return False
    async def process_retry_queue(self):
        """Stub for retry queue processing. Returns empty stats."""
        logger.info("process_retry_queue called (stub implementation)")
        return {"retried": 0, "successful": 0, "failed": 0}
    """
    Processes customer support queries in batches for efficient classification.
    Uses the async LLM wrapper to process queries concurrently with robust error handling
    and checkpoint-based recovery.
    """
    
    def __init__(self, 
                 mongodb_uri: str = None,
                 db_name: str = None,
                 source_collection: str = None,
                 target_collection: str = None,
                 batch_size: int = 10,
                 max_concurrent: int = 5,
                 batch_dir: str = "batch_files",
                 checkpoint_interval: int = 50,
                 mode: str = "batch",
                 continuous_interval: int = 60,
                 max_retries: int = 3):
        """
        Initialize the batch processor.
        
        Args:
            mongodb_uri: MongoDB connection URI
            db_name: MongoDB database name
            source_collection: MongoDB collection containing customer queries
            target_collection: MongoDB collection to store classifications
            batch_size: Number of documents to fetch in each batch
            max_concurrent: Maximum number of concurrent LLM calls
            batch_dir: Directory for storing batch files
            checkpoint_interval: Number of documents after which to save a checkpoint
            mode: Processing mode ("batch", "continuous", "scheduled")
            continuous_interval: Polling interval for continuous mode (seconds)
            max_retries: Maximum number of retries for failed operations
        """
        # MongoDB configuration
        self.mongodb_uri = mongodb_uri or os.getenv("MONGODB_URI")
        self.db_name = db_name or os.getenv("MONGODB_DB")
        self.source_collection_name = source_collection or os.getenv("MONGODB_SOURCE_COLLECTION")
        self.target_collection_name = target_collection or os.getenv("MONGODB_TARGET_COLLECTION")
        logger.info(f"[INIT] MongoDB URI: {self.mongodb_uri}")
        logger.info(f"[INIT] DB Name: {self.db_name}")
        logger.info(f"[INIT] Source Collection: {self.source_collection_name}")
        logger.info(f"[INIT] Target Collection: {self.target_collection_name}")
        
        # Batch processing configuration
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.batch_dir = batch_dir
        self.checkpoint_interval = checkpoint_interval
        self.mode = mode
        self.continuous_interval = continuous_interval
        self.max_retries = max_retries
        
        # Initialize components
        self.mongo_client = None
        self.batch_file_manager = BatchFileManager(batch_dir)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # State tracking
        self.job_id = f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.last_processed_id = None
        self.stats = {
            "job_id": self.job_id,
            "start_time": None,
            "end_time": None,
            "documents_processed": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "batches_processed": 0,
            "total_batches": 0,
            "duration_seconds": 0,
            "processing_rate": 0,  # documents per second
            "estimated_completion": None
        }
        
        # Ensure batch directory exists
        os.makedirs(self.batch_dir, exist_ok=True)

    @async_retry(max_retries=3, base_delay=2.0)
    async def connect(self, db_name: str = None):
        # Connect to MongoDB and initialize collections.
        # Args:
        #     db_name: Name of the MongoDB database
        try:
            logger.info(f"[CONNECT] MongoDB URI: {self.mongodb_uri}")
            logger.info(f"[CONNECT] DB Name: {db_name or self.db_name}")
            logger.info(f"[CONNECT] Source Collection: {self.source_collection_name}")
            logger.info(f"[CONNECT] Target Collection: {self.target_collection_name}")
            self.mongo_client = MongoClient(
                mongodb_uri=self.mongodb_uri,
                db_name=db_name or self.db_name,
                source_collection=self.source_collection_name,
                target_collection=self.target_collection_name
            )
            # The connect method doesn't return a value, it raises an exception on failure
            await self.mongo_client.connect()
            logger.info(f"[DEBUG] After connect: db={self.mongo_client.db}, source_collection={self.mongo_client.source_collection}, target_collection={self.mongo_client.target_collection}")
            try:
                count = await self.mongo_client.source_collection.count_documents({})
                logger.info(f"[DEBUG] Source collection document count: {count}")
            except Exception as e:
                logger.error(f"[DEBUG] Error counting documents in source collection: {e}")
            logger.info("Successfully connected to MongoDB")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            return False

    async def close(self):
    # Close the MongoDB connection.
        if self.mongo_client:
            await self.mongo_client.close()
            logger.info("MongoDB connection closed")
            
    async def load_checkpoint(self):
    # Load checkpoint data from previous processing runs.
        # Placeholder for actual implementation
        # Example: checkpoint = self.batch_file_manager.load_checkpoint()
        checkpoint = None
        if checkpoint:
            self.last_processed_id = checkpoint.get("last_processed_id")
            self.stats = checkpoint.get("stats", self.stats)
        return False
            
    async def save_checkpoint(self):
    # Save current processing state as a checkpoint.
        # Placeholder for actual implementation
        # Example: self.batch_file_manager.save_checkpoint({
        #     "last_processed_id": self.last_processed_id,
        #     "stats": self.stats,
        #     "timestamp": datetime.now(timezone.utc).isoformat()
        # })
        return False
    
    @async_retry(max_retries=3, base_delay=1.5)
    async def fetch_unprocessed_queries(self) -> Tuple[List[Dict[str, Any]], bool]:
        # Fetch a batch of unprocessed customer queries from the source collection. Uses cursor-based pagination for efficient retrieval.
        logger.info(f"[FETCH] DB: {self.db_name}, Source Collection: {self.source_collection_name}")
        try:
            documents, first_id, last_id = await self.mongo_client.fetch_unprocessed_documents(batch_size=self.batch_size)
            more_available = len(documents) >= self.batch_size
            logger.info(f"Fetched {len(documents)} documents from source collection (more_available={more_available})")
            return documents, more_available
        except Exception as e:
            logger.error(f"Error fetching unprocessed queries: {str(e)}")
            return [], False
    
    def _prepare_message(self, conversation: str, doc_id: str = None) -> List[Dict[str, str]]:
        # Prepare message for the LLM using the existing prompt builder.
        # Args:
        #     conversation: The customer conversation to classify
        #     doc_id: Optional document ID to use as conversation number
        # Returns:
        #     List[Dict]: The messages list with system prompt and few-shot examples
        try:
            conversation_number = str(doc_id) if doc_id else str(uuid.uuid4())
            prompt_result = build_prompt(
                conversation_number=conversation_number,
                aggregated_text=conversation
            )
            return prompt_result["messages"]
        except Exception as e:
            logger.error(f"Error preparing message: {str(e)}")
            return []
    
    async def process_batch(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Process a batch of customer queries concurrently.
        # Args:
        #     documents: List of documents containing unprocessed queries
        # Returns:
        #     Dict: Processing statistics
        batch_stats = {
            "total": len(documents),
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "start_time": datetime.now(timezone.utc),
            "end_time": None,
            "duration_seconds": None
        }
        
        if not documents:
            logger.info("No documents to process")
            batch_stats["end_time"] = datetime.now(timezone.utc)
            batch_stats["duration_seconds"] = (batch_stats["end_time"] - batch_stats["start_time"]).total_seconds()
            return batch_stats
        
        logger.info(f"Processing batch of {len(documents)} queries")
        
        # Create tasks for concurrent processing
        tasks = []
        
        for doc in documents:
            task = self._process_document(doc)
            tasks.append(task)
        
        # Run tasks concurrently with the semaphore limiting max concurrency
        results = await asyncio.gather(*tasks)
        
        # Update statistics
        for result in results:
            if result["status"] == "success":
                batch_stats["successful"] += 1
            else:
                batch_stats["failed"] += 1
                
            if result["retried"]:
                batch_stats["retried"] += 1
        
        batch_stats["end_time"] = datetime.now(timezone.utc)
        batch_stats["duration_seconds"] = (batch_stats["end_time"] - batch_stats["start_time"]).total_seconds()
        
        # Update global stats
        self.stats["documents_processed"] += batch_stats["total"]
        self.stats["successful"] += batch_stats["successful"]
        self.stats["failed"] += batch_stats["failed"]
        self.stats["retried"] += batch_stats["retried"]
        self.stats["batches_processed"] += 1
        
        # Calculate processing rate and estimated completion
        if self.stats["documents_processed"] > 0 and self.stats["start_time"]:
            elapsed = (datetime.now(timezone.utc) - self.stats["start_time"]).total_seconds()
            self.stats["duration_seconds"] = elapsed
            
            if elapsed > 0:
                self.stats["processing_rate"] = self.stats["documents_processed"] / elapsed
        
        # Save checkpoint if we've processed enough documents
        if self.stats["documents_processed"] % self.checkpoint_interval == 0:
            await self.save_checkpoint()
        
        logger.info(f"Batch processing completed: {batch_stats['successful']} successful, {batch_stats['failed']} failed, {batch_stats['retried']} retried")
        logger.info(f"Batch processing time: {batch_stats['duration_seconds']:.2f} seconds")
        
        return batch_stats
    
    async def _process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "status": "failure",
            "retried": False,
            "doc_id": document.get("_id", "unknown")
        }
        async with self.semaphore:
            try:
                doc_id = document["_id"]
                conversation_text = ""
                tweets = document.get("tweets", [])
                if tweets:
                    for tweet in tweets:
                        if isinstance(tweet, dict) and "text" in tweet:
                            sender = "Customer"
                            conversation_text += f"{sender}: {tweet['text']}\n"
                if not conversation_text.strip():
                    messages = document.get("messages", [])
                    for message in messages:
                        if isinstance(message, dict):
                            text = message.get("content") or message.get("text", "")
                            sender = message.get("sender", "Customer").capitalize()
                            conversation_text += f"{sender}: {text}\n"
                if not conversation_text.strip():
                    if "text" in document:
                        conversation_text = document["text"]
                    elif "content" in document:
                        conversation_text = document["content"]
                if not conversation_text.strip():
                    logger.warning(f"Document {doc_id} has no text content in any expected fields")
                    await self._mark_as_processed(doc_id, {"error": "No text content in document"})
                    return result
                logger.info(f"Processing conversation: {conversation_text[:100]}...")
                message = self._prepare_message(conversation=conversation_text, doc_id=str(doc_id))
                if not message:
                    logger.error(f"Failed to prepare message for document {doc_id}")
                    await self._mark_as_processed(doc_id, {"error": "Failed to prepare message"})
                    return result
                retry_count = 0
                max_attempts = self.max_retries + 1
                for attempt in range(1, max_attempts + 1):
                    try:
                        classification = await safe_ollama_classify_async(message)
                        if "error" in classification:
                            logger.warning(f"Classification attempt {attempt} failed for document {doc_id}: {classification['error']}")
                            if attempt < max_attempts:
                                retry_count += 1
                                backoff = 2 ** (attempt - 1)
                                logger.info(f"Retrying in {backoff} seconds...")
                                await asyncio.sleep(backoff)
                                continue
                            else:
                                logger.error(f"All classification attempts failed for document {doc_id}")
                                await self._mark_as_processed(doc_id, classification)
                                result["retried"] = retry_count > 0
                                return result
                        break
                    except Exception as e:
                        logger.warning(f"Classification attempt {attempt} error for document {doc_id}: {str(e)}")
                        if attempt < max_attempts:
                            retry_count += 1
                            backoff = 2 ** (attempt - 1)
                            logger.info(f"Retrying in {backoff} seconds...")
                            await asyncio.sleep(backoff)
                        else:
                            logger.error(f"All classification attempts failed for document {doc_id}: {str(e)}")
                            await self._mark_as_processed(doc_id, {"error": str(e)})
                            result["retried"] = retry_count > 0
                            return result
                output_doc = dict(document)
                if "_id" in output_doc:
                    del output_doc["_id"]  # Remove _id so MongoDB can auto-generate a new one
                if "status" in output_doc:
                    del output_doc["status"]  # Remove status field from processed output
                output_doc["source_document_id"] = document["_id"]  # Reference to original source document
                output_doc["classification"] = {
                    "intent": classification.get("intent", ""),
                    "topic": classification.get("topic", ""),
                    "sentiment": classification.get("sentiment", ""),
                    "categorization": classification.get("categorization", "")
                }
                output_doc["processed_at"] = datetime.now(timezone.utc)
                output_doc["retry_count"] = retry_count
                await self._store_classification(output_doc)
                await self._mark_as_processed(doc_id, {
                    "status": "processed",
                    "retry_count": retry_count
                })
                result["status"] = "success"
                result["retried"] = retry_count > 0
                return result
            except Exception as e:
                logger.error(f"Error processing document {document.get('_id', 'unknown')}: {str(e)}")
                await self._mark_as_processed(document.get("_id"), {"error": str(e)})
                return result
    
    @async_retry(max_retries=3, base_delay=1.5)
    async def _mark_as_processed(self, doc_id: Any, result: Dict[str, Any] = None) -> bool:
    # Mark a document as processed in the source collection. Uses retry logic for resilience.
        # Args:
        #     doc_id: ID of the document to mark
        #     result: Result information to store
        # Returns:
        #     bool: True if update was successful, False otherwise
        try:
            # Use correct method name with correct parameters
            status = "processed"
            result_id = result.get("result_id") if result and isinstance(result, dict) else None
            
            # Update document status using the correct method
            await self.mongo_client.update_document_status(
                doc_id=doc_id,
                status=status,
                result_id=result_id
            )
            
            logger.info(f"Document {doc_id} marked as {status}")
            return True
        except Exception as e:
            logger.error(f"Error marking document {doc_id} as processed: {str(e)}")
            # If we fail after retries, save to retry queue
        #     Dict: Processing statistics for retry queue
        retry_stats = {
            "retried": 0,
            "successful": 0,
            "failed": 0
        }
        
        try:
            # Get all items from the retry queue
            store_items = self.batch_file_manager.get_retry_queue_items("store")
            mark_items = self.batch_file_manager.get_retry_queue_items("mark")
            
            if not store_items and not mark_items:
                logger.info("No items in retry queue")
                return retry_stats
                
            logger.info(f"Processing retry queue: {len(store_items)} store items, {len(mark_items)} mark items")
            
            # Process store items
            for item_id, item_data in store_items.items():
                retry_stats["retried"] += 1
                try:
                    success = await self._store_classification(item_data)
                    if success:
                        retry_stats["successful"] += 1
                        self.batch_file_manager.remove_from_retry_queue("store", item_id)
                    else:
                        retry_stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Error processing retry item (store) {item_id}: {str(e)}")
                    retry_stats["failed"] += 1
            
            # Process mark items
            for item_id, item_data in mark_items.items():
                retry_stats["retried"] += 1
                try:
                    success = await self._mark_as_processed(item_id, item_data)
                    if success:
                        retry_stats["successful"] += 1
                        self.batch_file_manager.remove_from_retry_queue("mark", item_id)
                    else:
                        retry_stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Error processing retry item (mark) {item_id}: {str(e)}")
                    retry_stats["failed"] += 1
                    
            logger.info(f"Retry queue processing completed: {retry_stats['successful']} successful, {retry_stats['failed']} failed")
            return retry_stats
                
        except Exception as e:
            logger.error(f"Error processing retry queue: {str(e)}")
            return retry_stats

    async def run(self, continuous: bool = False, recover: bool = False) -> Dict[str, Any]:
    # Run the batch processor, optionally in continuous mode with recovery support.
        # Args:
        #     continuous: If True, run in continuous mode, processing batches until stopped
        #     recover: If True, attempt to recover from previous checkpoint
        # Returns:
        #     Dict: Summary of processing statistics
        # Connect to MongoDB
        connected = await self.connect()
        if not connected:
            return {"error": "Failed to connect to MongoDB", "job_id": self.job_id}
        
        # Set mode based on continuous parameter for backward compatibility
        if continuous:
            self.mode = "continuous"
            
        # Initialize statistics
        self.stats["start_time"] = datetime.now(timezone.utc)
        
        # Load checkpoint if recovering
        if recover:
            await self.load_checkpoint()
            logger.info(f"Recovering from checkpoint, last processed ID: {self.last_processed_id}")
            
            # Process retry queue first
            retry_stats = await self.process_retry_queue()
            logger.info(f"Processed {retry_stats['retried']} items from retry queue: {retry_stats['successful']} successful, {retry_stats['failed']} failed")
        
        try:
            # Main processing loop
            while True:
                documents, more_available = await self.fetch_unprocessed_queries()
                if not documents:
                    # No documents to process, exit loop
                    break
                # Actually process the batch of documents
                await self.process_batch(documents)
                # Process retry queue periodically
                if self.stats["batches_processed"] % 5 == 0:
                    await self.process_retry_queue()
                # Check for force exit after one batch (for debugging)
                if os.environ.get("BATCH_PROCESSOR_FORCE_EXIT_AFTER_BATCH") == "true":
                    logger.info("Force exit after processing one batch (BATCH_PROCESSOR_FORCE_EXIT_AFTER_BATCH=true)")
                    break
                # Check if we should exit (not continuous mode and no more documents)
                if not more_available and self.mode != "continuous":
                    logger.info("No more documents available, finishing processing")
                    break
                # Checkpoint regularly in continuous mode
                if self.mode == "continuous" and self.stats["batches_processed"] % 10 == 0:
                    await self.save_checkpoint()
        
        except asyncio.CancelledError:
            logger.info("Batch processor cancelled")
            await self.save_checkpoint()
        
        except Exception as e:
            logger.error(f"Error in batch processor: {str(e)}")
            self.stats["error"] = str(e)
            await self.save_checkpoint()
        
        finally:
            self.stats["end_time"] = datetime.now(timezone.utc)
            
            if self.stats["start_time"]:
                self.stats["duration_seconds"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            
            logger.info(f"Batch processor finished: {self.stats['documents_processed']} documents processed")
            logger.info(f"Successful: {self.stats['successful']}, Failed: {self.stats['failed']}, Retried: {self.stats['retried']}")
            logger.info(f"Total processing time: {self.stats['duration_seconds']:.2f} seconds")
            
            # Save final checkpoint
            await self.save_checkpoint()
            
            # Don't close connection if we're running in continuous mode and had no errors
            if self.mode != "continuous" or "error" in self.stats:
                await self.close()
            
            return self.stats


async def main():
    # Main function for command-line execution.
    import argparse
    
    parser = argparse.ArgumentParser(description="Process customer support queries in batches")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size")
    parser.add_argument("--concurrent", type=int, default=5, help="Max concurrent LLM calls")
    parser.add_argument("--mode", choices=["batch", "continuous", "scheduled"], default="batch",
                       help="Processing mode: batch (one-time), continuous (polling), or scheduled")
    parser.add_argument("--interval", type=int, default=60, 
                       help="Polling interval for continuous mode (seconds)")
    parser.add_argument("--batch-dir", default="batch_files", 
                       help="Directory for batch files and checkpoints")
    parser.add_argument("--checkpoint-interval", type=int, default=50,
                       help="Number of documents to process before checkpointing")
    parser.add_argument("--recover", action="store_true",
                       help="Recover from previous checkpoint")
    parser.add_argument("--retries", type=int, default=3,
                       help="Maximum number of retries for failed operations")
    
    # Legacy arguments for backward compatibility
    parser.add_argument("--continuous", action="store_true", help="Run in continuous mode (legacy)")
    parser.add_argument("--wait-time", type=int, default=60, help="Wait time between batches (legacy)")
    
    args = parser.parse_args()
    
    # Handle legacy arguments
    mode = args.mode
    if args.continuous:
        mode = "continuous"
    
    interval = args.interval
    if args.continuous and args.wait_time != 60:
        interval = args.wait_time
    
    processor = BatchProcessor(
        mongodb_uri=os.getenv("MONGODB_URI"),
        db_name=os.getenv("MONGODB_DB"),
        source_collection=os.getenv("MONGODB_SOURCE_COLLECTION"),
        target_collection=os.getenv("MONGODB_TARGET_COLLECTION"),
        batch_size=args.batch_size,
        max_concurrent=args.concurrent,
        batch_dir=args.batch_dir,
        checkpoint_interval=args.checkpoint_interval,
        mode=mode,
        continuous_interval=interval,
        max_retries=args.retries
    )
    
    stats = await processor.run(
        continuous=mode == "continuous",
        recover=args.recover
    )
    
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())