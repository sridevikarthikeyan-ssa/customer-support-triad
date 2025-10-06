"""
Simple test script for the enhanced batch processor.
This script focuses on testing the new features without MongoDB connection.
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

# Import our retry utilities
import sys
import os

# Add parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.retry_utils import async_retry

# Mock class for testing retry logic
class MockProcessor:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
        self.retry_counts = {}
        self.attempts = {}

    @async_retry(max_retries=3, base_delay=0.1)
    async def retry_operation(self, op_id, fail_times=0):
        """Test operation with retry logic."""
        # Track attempts
        if op_id not in self.attempts:
            self.attempts[op_id] = 0
        self.attempts[op_id] += 1
        
        # Simulate failures
        if self.attempts[op_id] <= fail_times:
            print(f"Operation {op_id} failing (attempt {self.attempts[op_id]}/{fail_times+1})...")
            raise Exception(f"Simulated failure for operation {op_id}")
        
        # Success after retries
        self.retry_counts[op_id] = self.attempts[op_id] - 1
        print(f"Operation {op_id} succeeded after {self.retry_counts[op_id]} retries!")
        return f"Result from {op_id}"

# Mock class for testing batch file management
class MockFileManager:
    def __init__(self, batch_dir="test_batch_files"):
        self.batch_dir = batch_dir
        os.makedirs(self.batch_dir, exist_ok=True)
        
    def save_checkpoint(self, job_id, checkpoint_data):
        """Save checkpoint to file."""
        filename = os.path.join(self.batch_dir, f"checkpoint_{job_id}.json")
        with open(filename, "w") as f:
            json.dump(checkpoint_data, f, default=str)
        print(f"Checkpoint saved to {filename}")
        return filename
        
    def load_latest_checkpoint(self):
        """Load the latest checkpoint."""
        checkpoints = [f for f in os.listdir(self.batch_dir) if f.startswith("checkpoint_")]
        if not checkpoints:
            return None
            
        # Get the most recent checkpoint
        latest = max(checkpoints, key=lambda x: os.path.getmtime(os.path.join(self.batch_dir, x)))
        filename = os.path.join(self.batch_dir, latest)
        
        with open(filename, "r") as f:
            data = json.load(f)
        print(f"Loaded checkpoint from {filename}")
        return data

# Mock batch processor
class MockBatchProcessor:
    def __init__(self, batch_size=5, max_concurrent=3):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.job_id = f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.stats = {
            "job_id": self.job_id,
            "start_time": None,
            "documents_processed": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0
        }
        self.file_manager = MockFileManager()
        self.retrier = MockProcessor()
        
    async def run_with_retries(self):
        """Run test operations with retry logic."""
        # Operations that succeed without retries
        result1 = await self.retrier.retry_operation("op1", fail_times=0)
        
        # Operation that needs retries but succeeds
        result2 = await self.retrier.retry_operation("op2", fail_times=2)
        
        # Operation that exceeds retry limit (should raise)
        try:
            result3 = await self.retrier.retry_operation("op3", fail_times=5)
        except Exception as e:
            print(f"Operation op3 failed after all retries: {e}")
            
        # Update stats
        self.stats["documents_processed"] = 3
        self.stats["successful"] = 2
        self.stats["failed"] = 1
        self.stats["retried"] = sum(self.retrier.retry_counts.values())
        
        # Save checkpoint
        self.file_manager.save_checkpoint(self.job_id, self.stats)
        
        return self.stats
        
    async def test_recovery(self):
        """Test checkpoint recovery."""
        # Generate checkpoint data
        checkpoint_data = {
            "job_id": self.job_id,
            "last_processed_id": "doc_123",
            "stats": {
                "documents_processed": 10,
                "successful": 8,
                "failed": 2,
                "retried": 3
            }
        }
        
        # Save checkpoint
        self.file_manager.save_checkpoint(self.job_id, checkpoint_data)
        
        # Simulate restart and load checkpoint
        loaded_data = self.file_manager.load_latest_checkpoint()
        
        # Verify recovery
        if loaded_data:
            print("\nCheckpoint Recovery Test:")
            print(f"Last processed ID: {loaded_data.get('last_processed_id')}")
            print(f"Documents processed: {loaded_data.get('stats', {}).get('documents_processed')}")
            return True
            
        return False

async def run_tests():
    """Run all tests."""
    print("=== TESTING ENHANCED BATCH PROCESSOR FEATURES ===\n")
    
    print("1. Testing retry logic with exponential backoff:")
    processor = MockBatchProcessor()
    stats = await processor.run_with_retries()
    
    print("\nRetry Statistics:")
    print(f"Operations processed: {stats['documents_processed']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Required retries: {stats['retried']}")
    
    print("\n2. Testing checkpoint-based recovery:")
    recovery_success = await processor.test_recovery()
    
    print("\n=== TEST SUMMARY ===")
    print(f"Retry Logic: {'✓ Passed' if stats['retried'] > 0 else '✗ Failed'}")
    print(f"Recovery System: {'✓ Passed' if recovery_success else '✗ Failed'}")
    print("================================")

if __name__ == "__main__":
    # Create batch directory if it doesn't exist
    os.makedirs("test_batch_files", exist_ok=True)
    
    # Run tests
    asyncio.run(run_tests())
    
    # Clean up test files
    for file in os.listdir("test_batch_files"):
        os.remove(os.path.join("test_batch_files", file))
    os.rmdir("test_batch_files")