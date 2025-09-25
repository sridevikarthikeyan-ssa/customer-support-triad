# Enhanced Batch Processor Implementation

This document describes the implementation details of the enhanced batch processor for customer support query classification.

## Overview

The batch processor has been enhanced with the following features:

1. **Robust Error Handling**
   - Retry logic with exponential backoff for transient failures
   - Comprehensive error handling for all operations
   - Detailed logging of all processing events

2. **Crash Recovery**
   - Checkpoint-based recovery system
   - Local batch file management for crash recovery
   - Retry queues for failed operations

3. **Performance Optimizations**
   - Cursor-based pagination for efficient database access
   - Configurable concurrency control
   - Progress tracking and performance metrics

4. **Multiple Processing Modes**
   - Batch mode (one-time processing)
   - Continuous mode (polling)
   - Scheduled mode (time-based)

## Components

### 1. BatchProcessor Class

The main batch processor class has been enhanced to support all the new features:

```python
class BatchProcessor:
    def __init__(self, 
                 mongodb_uri=None, 
                 source_collection="conversation_set",
                 target_collection="sentimental_analysis",
                 batch_size=10, 
                 max_concurrent=5,
                 batch_dir="batch_files", 
                 checkpoint_interval=50,
                 mode="batch",
                 continuous_interval=60,
                 max_retries=3):
        # ...initialization code...
```

The batch processor now uses the following components:
- `MongoClient`: For MongoDB connection and cursor-based pagination
- `BatchFileManager`: For managing batch files and checkpoints
- `RetryUtils`: For retry logic with exponential backoff

### 2. MongoDB Client

The MongoDB client handles connections and queries with cursor-based pagination:

```python
class MongoClient:
    def __init__(self, mongodb_uri, db_name, source_collection, target_collection):
        # ...initialization code...
        
    async def connect(self):
        # ...connect to MongoDB...
        
    async def get_unprocessed_documents(self, batch_size, last_id=None):
        # ...fetch documents with cursor-based pagination...
        
    async def store_classification(self, classification):
        # ...store classification result...
        
    async def mark_as_processed(self, doc_id, update_data):
        # ...mark document as processed...
```

### 3. Batch File Manager

The batch file manager handles local file storage for batch processing and crash recovery:

```python
class BatchFileManager:
    def __init__(self, batch_dir="batch_files"):
        # ...initialization code...
        
    def save_batch(self, batch_id, documents):
        # ...save batch file...
        
    def save_checkpoint(self, job_id, checkpoint_data):
        # ...save checkpoint...
        
    def load_latest_checkpoint(self):
        # ...load checkpoint...
        
    def add_to_retry_queue(self, queue_type, item_id, item_data):
        # ...add item to retry queue...
        
    def get_retry_queue_items(self, queue_type):
        # ...get items from retry queue...
        
    def remove_from_retry_queue(self, queue_type, item_id):
        # ...remove item from retry queue...
```

### 4. Retry Logic

The retry logic is implemented using decorators for async functions:

```python
async def async_retry(max_retries=3, delay_base=1.0):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # ...retry logic with exponential backoff...
        return wrapper
    return decorator
```

## Processing Flow

The enhanced batch processor follows this flow:

1. **Initialization**:
   - Set up MongoDB client, batch file manager, and semaphore
   - Create job ID and initialize statistics

2. **Connection**:
   - Connect to MongoDB with retry logic
   - Check for checkpoints if in recovery mode

3. **Batch Processing**:
   - Fetch unprocessed documents using cursor-based pagination
   - Save batch to local file for crash recovery
   - Process documents concurrently with semaphore for concurrency control
   - Use retry logic for LLM calls and database operations
   - Update statistics and save checkpoints periodically

4. **Retry Handling**:
   - Retry failed operations with exponential backoff
   - Add persistently failing operations to retry queues
   - Process retry queues periodically

5. **Continuous Mode**:
   - Poll for new documents periodically
   - Process batches as they become available
   - Save checkpoints regularly

6. **Finalization**:
   - Save final checkpoint
   - Close MongoDB connection if appropriate

## CLI Options

The batch processor now supports the following command-line options:

```
python -m batch_processor [options]

Options:
  --batch-size INT           Number of documents per batch
  --concurrent INT           Maximum concurrent LLM calls
  --mode MODE                Processing mode (batch, continuous, scheduled)
  --interval INT             Polling interval for continuous mode (seconds)
  --batch-dir PATH           Directory for batch files and checkpoints
  --checkpoint-interval INT  Number of documents to process before checkpointing
  --recover                  Recover from previous checkpoint
  --retries INT              Maximum number of retries for failed operations
```

## Testing

The enhanced batch processor includes comprehensive tests for all components:

- Unit tests for each component
- Integration tests for the whole system
- Mock MongoDB tests using mongomock-motor

## Demo Script

A demo script is provided in `utils/demo_enhanced_batch_processor.py` to showcase the enhanced features:

```
python utils/demo_enhanced_batch_processor.py [options]
```

The demo script supports all the batch processor options and can use either a real MongoDB connection or a mock database for testing.

## Next Steps

Potential future enhancements include:

1. Scheduled processing with cron-like syntax
2. Progress visualization and monitoring dashboard
3. Integration with notification systems for alerts
4. Advanced load balancing for large-scale processing
5. Multi-tenant support for shared processing resources