"""
Unit tests for the batch file manager module.
"""
import pytest
import os
import json
import shutil
from datetime import datetime, timezone
from unittest.mock import patch, mock_open

from utils.batch_file_manager import BatchFileManager

@pytest.fixture
def batch_file_manager():
    """Create a BatchFileManager instance for testing."""
    manager = BatchFileManager(
        batch_dir="test_batch_files",
        batch_size=10,
        checkpoint_interval=5
    )
    
    # Create directories
    os.makedirs(manager.batch_dir, exist_ok=True)
    os.makedirs(os.path.join(manager.batch_dir, "pending"), exist_ok=True)
    os.makedirs(os.path.join(manager.batch_dir, "completed"), exist_ok=True)
    os.makedirs(os.path.join(manager.batch_dir, "retry"), exist_ok=True)
    
    yield manager
    
    # Cleanup test directories
    def remove_dir_recursively(path):
        if os.path.exists(path):
            for entry in os.listdir(path):
                entry_path = os.path.join(path, entry)
                if os.path.isdir(entry_path):
                    remove_dir_recursively(entry_path)
                else:
                    try:
                        os.remove(entry_path)
                    except (PermissionError, OSError):
                        pass
            try:
                os.rmdir(path)
            except (PermissionError, OSError):
                pass
    
    remove_dir_recursively(manager.batch_dir)

class TestBatchFileManager:
    """Test suite for the BatchFileManager class."""
    
    def test_init(self):
        """Test initialization of BatchFileManager."""
        manager = BatchFileManager(
            batch_dir="test_init_batch_files",
            batch_size=20,
            checkpoint_interval=10
        )
        
        assert manager.batch_dir == "test_init_batch_files"
        assert manager.batch_size == 20
        assert manager.checkpoint_interval == 10
        assert manager.checkpoint_file == os.path.join("test_init_batch_files", "checkpoint.json")
        
        # Check that directories were created
        assert os.path.exists("test_init_batch_files")
        assert os.path.exists(os.path.join("test_init_batch_files", "pending"))
        assert os.path.exists(os.path.join("test_init_batch_files", "completed"))
        assert os.path.exists(os.path.join("test_init_batch_files", "retry"))
        
        # Clean up
        shutil.rmtree("test_init_batch_files")
    
    def test_generate_batch_id(self, batch_file_manager):
        """Test batch ID generation."""
        batch_id = batch_file_manager._generate_batch_id()
        
        assert isinstance(batch_id, str)
        assert batch_id.startswith("batch_")
        assert len(batch_id) > 6  # More than just "batch_"
    
    def test_get_pending_batches(self, batch_file_manager):
        """Test getting pending batch files."""
        # Create some test batch files
        test_files = [
            os.path.join(batch_file_manager.batch_dir, "pending", "batch_001.json"),
            os.path.join(batch_file_manager.batch_dir, "pending", "batch_002.json")
        ]
        
        for file_path in test_files:
            with open(file_path, "w") as f:
                f.write("{}")
        
        # Get the pending batches
        pending_batches = batch_file_manager.get_pending_batches()
        
        # Check that both files are returned
        assert len(pending_batches) == 2
        assert all(os.path.basename(file) in ["batch_001.json", "batch_002.json"] for file in pending_batches)
    
    def test_get_retry_queue_empty(self, batch_file_manager):
        """Test getting empty retry queue."""
        retry_queue = batch_file_manager.get_retry_queue()
        assert isinstance(retry_queue, list)
        assert len(retry_queue) == 0
    
    def test_get_retry_queue_with_items(self, batch_file_manager):
        """Test getting retry queue with items."""
        # Create a retry queue file
        retry_queue_path = os.path.join(batch_file_manager.batch_dir, "retry", "retry_queue.json")
        retry_items = [
            {"document": {"_id": "doc1"}, "error": "Error 1", "retry_type": "llm_failed"},
            {"document": {"_id": "doc2"}, "error": "Error 2", "retry_type": "write_failed"}
        ]
        
        with open(retry_queue_path, "w") as f:
            json.dump(retry_items, f)
        
        # Get the retry queue
        retry_queue = batch_file_manager.get_retry_queue()
        
        # Check the contents
        assert len(retry_queue) == 2
        assert retry_queue[0]["document"]["_id"] == "doc1"
        assert retry_queue[1]["document"]["_id"] == "doc2"
    
    def test_add_to_retry_queue_new(self, batch_file_manager):
        """Test adding to a new retry queue."""
        document = {"_id": "doc1", "text": "Test"}
        error = "Test error"
        retry_type = "llm_failed"
        
        batch_file_manager.add_to_retry_queue(document, error, retry_type)
        
        # Check that the retry queue file was created
        retry_queue_path = os.path.join(batch_file_manager.batch_dir, "retry", "retry_queue.json")
        assert os.path.exists(retry_queue_path)
        
        # Check the contents
        with open(retry_queue_path, "r") as f:
            retry_queue = json.load(f)
            
            assert len(retry_queue) == 1
            assert retry_queue[0]["document"]["_id"] == "doc1"
            assert retry_queue[0]["error"] == "Test error"
            assert retry_queue[0]["retry_type"] == "llm_failed"
    
    def test_add_to_retry_queue_existing(self, batch_file_manager):
        """Test adding to an existing retry queue."""
        # Create an initial retry queue
        retry_queue_path = os.path.join(batch_file_manager.batch_dir, "retry", "retry_queue.json")
        initial_items = [
            {"document": {"_id": "doc1"}, "error": "Error 1", "retry_type": "llm_failed", "attempts": 1}
        ]
        
        with open(retry_queue_path, "w") as f:
            json.dump(initial_items, f)
        
        # Add another document
        document = {"_id": "doc2", "text": "Test"}
        batch_file_manager.add_to_retry_queue(document, "Error 2", "write_failed")
        
        # Check the contents
        with open(retry_queue_path, "r") as f:
            retry_queue = json.load(f)
            
            assert len(retry_queue) == 2
            assert retry_queue[0]["document"]["_id"] == "doc1"
            assert retry_queue[1]["document"]["_id"] == "doc2"
    
    def test_remove_from_retry_queue(self, batch_file_manager):
        """Test removing from retry queue."""
        # Create a retry queue
        retry_queue_path = os.path.join(batch_file_manager.batch_dir, "retry", "retry_queue.json")
        initial_items = [
            {"document": {"_id": "doc1"}, "error": "Error 1", "retry_type": "llm_failed"},
            {"document": {"_id": "doc2"}, "error": "Error 2", "retry_type": "write_failed"}
        ]
        
        with open(retry_queue_path, "w") as f:
            json.dump(initial_items, f)
        
        # Remove one item
        batch_file_manager.remove_from_retry_queue("doc1")
        
        # Check the contents
        with open(retry_queue_path, "r") as f:
            retry_queue = json.load(f)
            
            assert len(retry_queue) == 1
            assert retry_queue[0]["document"]["_id"] == "doc2"
    
    def test_create_batch_file(self, batch_file_manager):
        """Test creating a batch file."""
        documents = [
            {"_id": f"doc{i}", "text": f"Test {i}"} for i in range(1, 6)
        ]
        
        first_id = "doc1"
        last_id = "doc5"
        batch_id = "test_batch_001"
        
        batch_path = batch_file_manager.create_batch_file(documents, first_id, last_id, batch_id)
        
        # Check that the file exists
        assert os.path.exists(batch_path)
        
        # Check the contents
        with open(batch_path, "r") as f:
            batch_data = json.load(f)
            
            assert batch_data["metadata"]["batch_id"] == batch_id
            assert batch_data["metadata"]["first_object_id"] == first_id
            assert batch_data["metadata"]["last_object_id"] == last_id
            assert batch_data["metadata"]["document_count"] == 5
            assert len(batch_data["documents"]) == 5
    
    def test_mark_batch_completed(self, batch_file_manager):
        """Test marking a batch as completed."""
        # Create a test batch file
        batch_id = "test_batch_001"
        source_path = os.path.join(batch_file_manager.batch_dir, "pending", f"{batch_id}.json")
        
        batch_data = {
            "metadata": {
                "batch_id": batch_id,
                "document_count": 5,
                "status": "pending"
            },
            "documents": [{"_id": f"doc{i}"} for i in range(1, 6)]
        }
        
        with open(source_path, "w") as f:
            json.dump(batch_data, f)
        
        # Mark the batch as completed
        batch_file_manager.mark_batch_completed(batch_id)
        
        # Check that the source file no longer exists
        assert not os.path.exists(source_path)
        
        # Check that the target file exists
        target_path = os.path.join(batch_file_manager.batch_dir, "completed", f"{batch_id}.json")
        assert os.path.exists(target_path)
        
        # Check the contents
        with open(target_path, "r") as f:
            completed_data = json.load(f)
            
            assert completed_data["metadata"]["status"] == "completed"
            assert "completed_at" in completed_data["metadata"]
    
    def test_save_checkpoint(self, batch_file_manager):
        """Test saving checkpoint."""
        last_processed_id = "doc123"
        stats = {
            "documents_processed": 10,
            "successful": 8,
            "failed": 2
        }
        
        batch_file_manager.save_checkpoint(last_processed_id, stats)
        
        # Check that the checkpoint file exists
        assert os.path.exists(batch_file_manager.checkpoint_file)
        
        # Check the contents
        with open(batch_file_manager.checkpoint_file, "r") as f:
            checkpoint_data = json.load(f)
            
            assert checkpoint_data["last_processed_object_id"] == last_processed_id
            assert checkpoint_data["stats"]["documents_processed"] == 10
    
    def test_load_checkpoint(self, batch_file_manager):
        """Test loading checkpoint."""
        # Create a test checkpoint file
        checkpoint_data = {
            "last_processed_object_id": "doc123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "documents_processed": 10,
                "successful": 8,
                "failed": 2
            }
        }
        
        with open(batch_file_manager.checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)
        
        # Load the checkpoint
        loaded_data = batch_file_manager.load_checkpoint()
        
        # Check the contents
        assert loaded_data["last_processed_object_id"] == "doc123"
        assert loaded_data["stats"]["documents_processed"] == 10
    
    def test_load_checkpoint_no_file(self, batch_file_manager):
        """Test loading checkpoint when no file exists."""
        loaded_data = batch_file_manager.load_checkpoint()
        assert loaded_data == {}