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
import asyncio
import json
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


class BatchProcessor:
    """
    Processes customer support queries in batches for efficient classification.
    Uses the async LLM wrapper to process queries concurrently with robust error handling
    and checkpoint-based recovery.
    """
    
    def __init__(self, 
                 mongodb_uri: str = None,
                 source_collection: str = "conversation_set",
                 target_collection: str = "sentimental_analysis",
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
        self.mongodb_uri = mongodb_uri or os.getenv(
            "MONGODB_URI", 
            "mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT"
        )
        self.source_collection_name = source_collection
        self.target_collection_name = target_collection
        
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
    async def connect(self, db_name: str = "customer_support_triad"):
        """
        Connect to MongoDB and initialize collections.
        
        Args:
            db_name: Name of the MongoDB database
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to MongoDB: {self.mongodb_uri}")
            self.mongo_client = MongoClient(
                mongodb_uri=self.mongodb_uri,
                db_name=db_name,
                source_collection=self.source_collection_name,
                target_collection=self.target_collection_name
            )
            
            # The connect method doesn't return a value, it raises an exception on failure
            await self.mongo_client.connect()
            logger.info("Successfully connected to MongoDB")
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            return False

    async def close(self):
        """Close the MongoDB connection."""
        if self.mongo_client:
            await self.mongo_client.close()
            logger.info("MongoDB connection closed")
            
    async def load_checkpoint(self):
        """
        Load checkpoint data from previous processing runs.
        
        Returns:
            bool: True if checkpoint loaded successfully, False otherwise
        """
        try:
            checkpoint = self.batch_file_manager.load_latest_checkpoint()
            if checkpoint:
                self.last_processed_id = checkpoint.get("last_processed_id")
                self.stats = checkpoint.get("stats", self.stats)
                logger.info(f"Loaded checkpoint: last processed ID: {self.last_processed_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading checkpoint: {str(e)}")
            return False
            
    async def save_checkpoint(self):
        """
        Save current processing state as a checkpoint.
        
        Returns:
            bool: True if checkpoint saved successfully, False otherwise
        """
        try:
            checkpoint_data = {
                "last_processed_id": self.last_processed_id,
                "stats": self.stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.batch_file_manager.save_checkpoint(self.job_id, checkpoint_data)
            logger.info(f"Saved checkpoint: last processed ID: {self.last_processed_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving checkpoint: {str(e)}")
            return False
    
    @async_retry(max_retries=3, base_delay=1.5)
    async def fetch_unprocessed_queries(self) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Fetch a batch of unprocessed customer queries from the source collection.
        Uses cursor-based pagination for efficient retrieval.
        
        Returns:
            Tuple[List[Dict], bool]: List of documents and a flag indicating if more documents are available
        """
        try:
            # Use cursor-based pagination from our MongoClient - fixed method name
            documents, first_id, last_id = await self.mongo_client.fetch_unprocessed_documents(
                batch_size=self.batch_size, 
                last_object_id=self.last_processed_id
            )
            
            more_available = len(documents) >= self.batch_size  # If we got a full batch, assume more are available
            
            if documents:
                self.last_processed_id = last_id
                
                # Save to batch file for recovery
                batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                self.batch_file_manager.save_batch(batch_id, documents)
                
                logger.info(f"Fetched {len(documents)} unprocessed queries (more available: {more_available})")
            else:
                logger.info("No unprocessed queries found")
                
            return documents, more_available
        
        except Exception as e:
            logger.error(f"Error fetching unprocessed queries: {str(e)}")
            return [], False
    
    def _prepare_message(self, conversation: str) -> List[Dict[str, str]]:
        """
        Prepare message for the LLM.
        
        Args:
            conversation: The customer conversation to classify
            
        Returns:
            List[Dict]: The message for the LLM in the required format
        """
        return [{
            "role": "user",
            "content": (
                f"Please classify this customer conversation in JSON format with the following fields:\n"
                f"- 'categorization': A brief phrase describing the main issue or request\n"
                f"- 'intent': The customer's primary intention (e.g., Technical Support, Complaint, Inquiry)\n"
                f"- 'topic': The subject matter area (e.g., Account/Billing, Technical, Product Info)\n"
                f"- 'sentiment': The emotional tone (e.g., Positive, Negative, Neutral)\n\n"
                f"Conversation: {conversation[:1000]}"
            )
        }]
    
    async def process_batch(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of customer queries concurrently.
        
        Args:
            documents: List of documents containing unprocessed queries
            
        Returns:
            Dict: Processing statistics
        """
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
        """
        Process a single document with semaphore for concurrency control.
        Uses retry logic for resilience.
        
        Args:
            document: The document containing the customer conversation to process
            
        Returns:
            Dict: Processing result with status and retry information
        """
        result = {
            "status": "failure",
            "retried": False,
            "doc_id": document.get("_id", "unknown")
        }
        
        async with self.semaphore:
            try:
                doc_id = document["_id"]
                
                # Try to extract text from various possible field structures
                conversation_text = ""
                
                # Try tweets field first (most likely structure)
                tweets = document.get("tweets", [])
                if tweets:
                    for tweet in tweets:
                        if isinstance(tweet, dict) and "text" in tweet:
                            conversation_text += tweet["text"] + " "
                
                # If no text found in tweets, try messages field
                if not conversation_text.strip():
                    messages = document.get("messages", [])
                    for message in messages:
                        if isinstance(message, dict) and "content" in message:
                            conversation_text += message["content"] + " "
                        elif isinstance(message, dict) and "text" in message:
                            conversation_text += message["text"] + " "
                
                # If still no text, try direct text field
                if not conversation_text.strip():
                    if "text" in document:
                        conversation_text = document["text"]
                    elif "content" in document:
                        conversation_text = document["content"]
                
                # Final check for conversation text
                if not conversation_text.strip():
                    logger.warning(f"Document {doc_id} has no text content in any expected fields")
                    await self._mark_as_processed(doc_id, {"error": "No text content in document"})
                    return result
                
                logger.info(f"Processing conversation: {conversation_text[:100]}...")
                
                # Call LLM for classification with retry logic
                message = self._prepare_message(conversation_text)
                
                # Use retry logic for LLM calls
                retry_count = 0
                max_attempts = self.max_retries + 1  # +1 for initial attempt
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        classification = await safe_ollama_classify_async(message)
                        
                        # Check if classification was successful
                        if "error" in classification:
                            logger.warning(f"Classification attempt {attempt} failed for document {doc_id}: {classification['error']}")
                            if attempt < max_attempts:
                                retry_count += 1
                                backoff = 2 ** (attempt - 1)  # Exponential backoff
                                logger.info(f"Retrying in {backoff} seconds...")
                                await asyncio.sleep(backoff)
                                continue
                            else:
                                logger.error(f"All classification attempts failed for document {doc_id}")
                                await self._mark_as_processed(doc_id, classification)
                                result["retried"] = retry_count > 0
                                return result
                        
                        # We have a successful classification
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
                
                # Add required fields to the classification result
                classification_result = {
                    "document_id": doc_id,
                    "conversation": conversation_text[:1000],  # Limit text size
                    "intent": classification.get("intent", ""),
                    "topic": classification.get("topic", ""),
                    "sentiment": classification.get("sentiment", ""),
                    "processed_at": datetime.now(timezone.utc),
                    "retry_count": retry_count
                }
                
                # Store the classification result
                await self._store_classification(classification_result)
                
                # Mark the source document as processed
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
    async def _store_classification(self, classification: Dict[str, Any]) -> bool:
        """
        Store the classification result in the target collection.
        Uses retry logic for resilience.
        
        Args:
            classification: The classification result to store
            
        Returns:
            bool: True if storage was successful, False otherwise
        """
        try:
            # Get the original document to extract the conversation number
            source_doc_id = classification['document_id']
            
            # Try to fetch the source document to get the actual conversation number and tweets
            conversation_number = str(source_doc_id)  # Default fallback
            original_tweets = None  # Default to None for tweets
            try:
                source_doc = await self.mongo_client.db[self.mongo_client.source_collection_name].find_one(
                    {"_id": source_doc_id}
                )
                
                # If we have a source document, extract data from it
                if source_doc:
                    # 1. Extract conversation number
                    if "conversation_number" in source_doc:
                        conversation_number = source_doc["conversation_number"]
                    elif "ticket_id" in source_doc:
                        conversation_number = source_doc["ticket_id"]
                    elif "conversation_id" in source_doc:
                        conversation_number = source_doc["conversation_id"]
                    elif "id" in source_doc:
                        conversation_number = source_doc["id"]
                    else:
                        # Get the count of documents in target collection and add 1
                        count = await self.mongo_client.db[self.mongo_client.target_collection_name].count_documents({})
                        conversation_number = str(count + 1)
                    
                    # 2. Extract original tweets if available
                    if "tweets" in source_doc and source_doc["tweets"]:
                        # Use the original tweets array
                        original_tweets = source_doc["tweets"]
                    else:
                        # Create tweets array with the conversation text
                        original_tweets = []
                        # Try to extract the content from different possible fields
                        if "conversation" in classification and classification["conversation"]:
                            original_tweets = [{"text": classification["conversation"]}]
                        elif "content" in source_doc:
                            original_tweets = [{"text": source_doc["content"]}]
                        elif "message" in source_doc:
                            original_tweets = [{"text": source_doc["message"]}]
                        # If no content was found, create a simple tweet object
                        if not original_tweets:
                            original_tweets = [{"text": "No content available"}]
                            
            except Exception as e:
                logger.warning(f"Failed to fetch source document data: {str(e)}")
                # Create a simple tweet object with the conversation if available
                if "conversation" in classification and classification["conversation"]:
                    original_tweets = [{"text": classification["conversation"]}]
            
            # Create a more complete document with required fields
            document = {
                "_id": source_doc_id,
                "conversation_number": conversation_number,  # Use actual conversation number if available
                "source_object_id": str(source_doc_id),  # Always use source doc ID for this field
                "processing_attempts": 1,  # Initialize processing attempts
                "messages": None,  # Set messages to null as in the example
                "tweets": original_tweets  # Use original tweets if available
            }
            
            # Extract the classification fields to match the expected format including categorization
            conversation_text = classification.get("conversation", "")
            # Generate a categorization based on intent and topic
            categorization = f"{classification.get('intent', 'General')} regarding {classification.get('topic', 'general inquiry')}"
            
            classification_data = {
                "categorization": categorization,  # Add categorization field
                "intent": classification.get("intent", ""),
                "topic": classification.get("topic", ""),
                "sentiment": classification.get("sentiment", "")
            }
            
            # Store the classification in MongoDB
            result_id = await self.mongo_client.store_classification_result(
                document=document,
                classification=classification_data,
                batch_job_id=self.job_id,
                tweets=original_tweets  # Pass the tweets array to maintain the proper structure
            )
            
            logger.info(f"Classification stored for document {classification['document_id']} with result_id {result_id}")
            
            # Update the source document with the result ID
            await self._mark_as_processed(classification['document_id'], {"result_id": result_id})
            
            return True
        except Exception as e:
            logger.error(f"Error storing classification: {str(e)}")
            # If we fail after retries, save to retry queue
            doc_id = classification.get("document_id")
            if doc_id:
                self.batch_file_manager.add_to_retry_queue("store", doc_id, classification)
                logger.info(f"Added document {doc_id} to storage retry queue")
            return False
    
    @async_retry(max_retries=3, base_delay=1.5)
    async def _mark_as_processed(self, doc_id: Any, result: Dict[str, Any] = None) -> bool:
        """
        Mark a document as processed in the source collection.
        Uses retry logic for resilience.
        
        Args:
            doc_id: ID of the document to mark
            result: Result information to store
            
        Returns:
            bool: True if update was successful, False otherwise
        """
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
            if doc_id:
                update_data = {
                    "status": "processed",
                    "result_id": result.get("result_id") if result and isinstance(result, dict) else None
                }
                self.batch_file_manager.add_to_retry_queue("mark", doc_id, update_data)
                logger.info(f"Added document {doc_id} to marking retry queue")
            return False
    
    async def process_retry_queue(self):
        """
        Process items in the retry queue.
        
        Returns:
            Dict: Processing statistics for retry queue
        """
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
        """
        Run the batch processor, optionally in continuous mode with recovery support.
        
        Args:
            continuous: If True, run in continuous mode, processing batches until stopped
            recover: If True, attempt to recover from previous checkpoint
            
        Returns:
            Dict: Summary of processing statistics
        """
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
                    if self.mode != "continuous":
                        logger.info("No more documents to process")
                        break
                        
                    # In continuous mode, we wait and then check again
                    logger.info(f"No documents to process, waiting {self.continuous_interval} seconds...")
                    await asyncio.sleep(self.continuous_interval)
                    continue
                
                # Process the batch
                batch_stats = await self.process_batch(documents)
                
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
    """Main function for command-line execution."""
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