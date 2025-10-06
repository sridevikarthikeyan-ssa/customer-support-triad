"""
Batch file manager for handling local file cache of MongoDB conversations.
Provides functionality for creating and managing batch files, retry queues, and checkpoints.
"""

import os
import json
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import shutil
from logger import logger

class BatchFileManager:
    """Manages batch file creation, tracking, and recovery for MongoDB batch processing."""
    
    def __init__(
        self,
        batch_dir: str = "batch_files",
        batch_size: int = 100,
        checkpoint_interval: int = 50,
    ):
        """
        Initialize the batch file manager.
        
        Args:
            batch_dir: Directory to store batch files
            batch_size: Number of documents per batch file
            checkpoint_interval: Number of documents after which to create a checkpoint
        """
        self.batch_dir = batch_dir
        self.batch_size = batch_size
        self.checkpoint_interval = checkpoint_interval
        self.current_batch_id = None
        self.checkpoint_file = os.path.join(batch_dir, "checkpoint.json")
        
        # Ensure batch directory exists
        os.makedirs(batch_dir, exist_ok=True)
        os.makedirs(os.path.join(batch_dir, "pending"), exist_ok=True)
        os.makedirs(os.path.join(batch_dir, "completed"), exist_ok=True)
        os.makedirs(os.path.join(batch_dir, "retry"), exist_ok=True)
    
    def _generate_batch_id(self) -> str:
        """Generate a unique batch ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"batch_{timestamp}"
    
    def get_pending_batches(self) -> List[str]:
        """Get list of pending batch files."""
        pending_dir = os.path.join(self.batch_dir, "pending")
        if not os.path.exists(pending_dir):
            return []
        return sorted([
            os.path.join(pending_dir, f) for f in os.listdir(pending_dir)
            if f.endswith(".json")
        ])
    
    def get_retry_queue(self) -> List[Dict[str, Any]]:
        """Get documents from the retry queue."""
        retry_queue_path = os.path.join(self.batch_dir, "retry", "retry_queue.json")
        if not os.path.exists(retry_queue_path):
            return []
        
        try:
            with open(retry_queue_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Failed to load retry queue from {retry_queue_path}")
            return []
    
    def add_to_retry_queue(self, document: Dict[str, Any], error: str, retry_type: str = "llm_failed") -> None:
        """
        Add a failed document to the retry queue.
        
        Args:
            document: The document that failed processing
            error: The error message
            retry_type: Type of retry needed ("llm_failed" or "write_failed")
        """
        retry_queue_path = os.path.join(self.batch_dir, "retry", "retry_queue.json")
        
        # Load existing queue or create new one
        try:
            if os.path.exists(retry_queue_path):
                with open(retry_queue_path, 'r') as f:
                    retry_queue = json.load(f)
            else:
                retry_queue = []
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Failed to load retry queue, creating new one")
            retry_queue = []
        
        # Add the document to the retry queue
        retry_item = {
            "document": document,
            "error": error,
            "retry_type": retry_type,
            "attempts": document.get("processing_attempts", 0) + 1,
            "last_attempt": datetime.now(timezone.utc).isoformat(),
        }
        
        # Check if this document is already in the queue
        doc_id = document.get("_id")
        existing_items = [item for item in retry_queue if item.get("document", {}).get("_id") == doc_id]
        
        if existing_items:
            # Update the existing item
            for item in existing_items:
                item.update(retry_item)
        else:
            # Add as new item
            retry_queue.append(retry_item)
        
        # Save the updated queue
        with open(retry_queue_path, 'w') as f:
            json.dump(retry_queue, f, indent=2, default=str)
    
    def remove_from_retry_queue(self, document_id: str) -> None:
        """Remove a document from the retry queue."""
        retry_queue_path = os.path.join(self.batch_dir, "retry", "retry_queue.json")
        
        if not os.path.exists(retry_queue_path):
            return
        
        try:
            with open(retry_queue_path, 'r') as f:
                retry_queue = json.load(f)
            
            # Filter out the document
            retry_queue = [item for item in retry_queue 
                          if item.get("document", {}).get("_id") != document_id]
            
            with open(retry_queue_path, 'w') as f:
                json.dump(retry_queue, f, indent=2, default=str)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to update retry queue: {e}")
    
    def save_batch(self, batch_id: str, documents: List[Dict[str, Any]]) -> str:
        """
        Save a batch of documents to a file.
        
        Args:
            batch_id: The ID of the batch
            documents: List of documents to save
            
        Returns:
            The path to the created batch file
        """
        batch_metadata = {
            "batch_id": batch_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(documents),
            "status": "pending"
        }
        
        batch_data = {
            "metadata": batch_metadata,
            "documents": documents
        }
        
        batch_file_path = os.path.join(self.batch_dir, "pending", f"{batch_id}.json")
        with open(batch_file_path, 'w') as f:
            json.dump(batch_data, f, indent=2, default=str)
        
        logger.info(f"Saved batch file {batch_file_path} with {len(documents)} documents")
        return batch_file_path
    
    def get_retry_queue_items(self, queue_type: str) -> Dict[str, Dict[str, Any]]:
        """
        Get items from a specific retry queue.
        
        Args:
            queue_type: Type of retry queue ("store" or "mark")
            
        Returns:
            Dictionary of items from the retry queue
        """
        retry_dir = os.path.join(self.batch_dir, "retry")
        retry_file = os.path.join(retry_dir, f"{queue_type}_retry_queue.json")
        
        if not os.path.exists(retry_file):
            return {}
        
        try:
            with open(retry_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Failed to load {queue_type} retry queue")
            return {}
    
    def create_batch_file(
        self,
        documents: List[Dict[str, Any]],
        first_object_id: Optional[str] = None,
        last_object_id: Optional[str] = None,
        batch_id: Optional[str] = None
    ) -> str:
        """
        Create a new batch file with the given documents.
        
        Args:
            documents: List of documents to include in the batch
            first_object_id: The ObjectId of the first document (for pagination)
            last_object_id: The ObjectId of the last document (for pagination)
            batch_id: Optional batch ID to use (generated if not provided)
            
        Returns:
            The path to the created batch file
        """
        batch_id = batch_id or self._generate_batch_id()
        self.current_batch_id = batch_id
        
        batch_metadata = {
            "batch_id": batch_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(documents),
            "first_object_id": first_object_id,
            "last_object_id": last_object_id,
            "status": "pending"
        }
        
        batch_data = {
            "metadata": batch_metadata,
            "documents": documents
        }
        
        batch_file_path = os.path.join(self.batch_dir, "pending", f"{batch_id}.json")
        with open(batch_file_path, 'w') as f:
            json.dump(batch_data, f, indent=2, default=str)
        
        logger.info(f"Created batch file {batch_file_path} with {len(documents)} documents")
        return batch_file_path
    
    def mark_batch_completed(self, batch_id: str) -> None:
        """
        Mark a batch as completed by moving it to the completed directory.
        
        Args:
            batch_id: The ID of the batch to mark as completed
        """
        source_path = os.path.join(self.batch_dir, "pending", f"{batch_id}.json")
        target_path = os.path.join(self.batch_dir, "completed", f"{batch_id}.json")
        
        if not os.path.exists(source_path):
            logger.warning(f"Batch file {source_path} not found, cannot mark as completed")
            return
        
        # Update the batch metadata to reflect completion
        try:
            with open(source_path, 'r') as f:
                batch_data = json.load(f)
            
            batch_data["metadata"]["status"] = "completed"
            batch_data["metadata"]["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            with open(target_path, 'w') as f:
                json.dump(batch_data, f, indent=2, default=str)
            
            # Remove the original file
            os.remove(source_path)
            logger.info(f"Marked batch {batch_id} as completed")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Failed to mark batch {batch_id} as completed: {e}")
            # Try to move the file anyway
            try:
                shutil.move(source_path, target_path)
            except Exception as e:
                logger.error(f"Failed to move batch file: {e}")
    
    def save_checkpoint(self, last_processed_object_id: str, progress_stats: Dict[str, Any]) -> None:
        """
        Save a checkpoint with the last processed ObjectId.
        
        Args:
            last_processed_object_id: The ObjectId of the last processed document
            progress_stats: Statistics about processing progress
        """
        checkpoint_data = {
            "last_processed_object_id": last_processed_object_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": progress_stats
        }
        
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
        
        logger.info(f"Saved checkpoint: last_processed_object_id={last_processed_object_id}")
    
    def load_checkpoint(self) -> Dict[str, Any]:
        """
        Load the last checkpoint.
        
        Returns:
            Dictionary with checkpoint data or empty dict if no checkpoint exists
        """
        if not os.path.exists(self.checkpoint_file):
            logger.info("No checkpoint file found")
            return {}
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            logger.info(f"Loaded checkpoint: last_processed_object_id={checkpoint_data.get('last_processed_object_id')}")
            return checkpoint_data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return {}
            
    def load_latest_checkpoint(self) -> Dict[str, Any]:
        """
        Load the latest checkpoint (alias for load_checkpoint).
        
        Returns:
            Dictionary with checkpoint data or empty dict if no checkpoint exists
        """
        return self.load_checkpoint()