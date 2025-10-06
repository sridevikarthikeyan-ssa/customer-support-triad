# Batch Processor Implementation

## Overview

The batch processor component provides an asynchronous batch processing system for customer support query classification. It fetches unprocessed queries from MongoDB in batches, classifies them using the LLM wrapper, and stores the results back in MongoDB.

## Architecture

The batch processor follows a producer-consumer pattern with these key components:

1. **MongoDB Connection**: Connects to MongoDB collections for storing queries and classification results
2. **Query Fetcher**: Retrieves batches of unprocessed queries
3. **Processor Pool**: Processes queries concurrently using async tasks
4. **Result Storage**: Stores classification results back in MongoDB

## Components

### BatchProcessor Class

The core class that orchestrates the batch processing workflow:

```python
class BatchProcessor:
    def __init__(self, 
                 mongodb_uri: str = None,
                 source_collection: str = "conversation_set",
                 target_collection: str = "sentimental_analysis",
                 batch_size: int = 10,
                 max_concurrent: int = 5):
        # Initialize connection parameters
        
    async def connect(self):
        # Connect to MongoDB
        
    async def fetch_unprocessed_queries(self):
        # Fetch a batch of unprocessed queries
        
    async def process_document(self, document):
        # Process a single document using the LLM wrapper
        
    async def process_batch(self, batch):
        # Process a batch of documents concurrently
        
    async def run(self):
        # Run the batch processor until all documents are processed
        
    async def close(self):
        # Close the MongoDB connection
```

### CLI Interface

A command-line interface for running the batch processor with various options:

```bash
python cli.py [options]
```

Options include:
- Batch size and concurrency settings
- MongoDB connection parameters
- Logging level
- Output file for results
- Dry-run mode

### Demo Script

A demonstration script that creates a mock MongoDB environment for testing:

```python
class MockBatchProcessor(BatchProcessor):
    async def _process_document(self, document):
        # Override with mock classification logic
```

## Data Flow

1. User runs the batch processor via CLI
2. BatchProcessor connects to MongoDB
3. BatchProcessor fetches a batch of unprocessed queries
4. BatchProcessor processes the batch concurrently
5. Results are stored back in MongoDB
6. Process repeats until all queries are processed
7. Summary statistics are returned to the user

## MongoDB Schema

### Queries Collection

```json
{
  "_id": "doc_id",
  "text": "Customer query text",
  "metadata": {
    "source": "email",
    "timestamp": "2025-09-23T10:30:00Z"
  },
  "processed": false,
  "processing_attempts": 0
}
```

### Results Collection

```json
{
  "query_id": "doc_id",
  "classification": {
    "intent": "troubleshooting",
    "topic": "account_access",
    "sentiment": "neutral"
  },
  "processed_at": "2025-09-23T12:45:00Z"
}
```

## Concurrency Management

The batch processor uses asyncio for concurrent processing:

1. Semaphore limits maximum concurrent tasks
2. Each document is processed in its own task
3. Batch size controls how many documents are fetched at once
4. Error handling isolates failures to individual documents

## Error Handling

The batch processor includes comprehensive error handling:

1. Connection errors: Attempts to reconnect with backoff
2. Processing errors: Failed documents are tracked but don't stop the batch
3. Invalid classifications: Validation before storage
4. Timeouts: Configurable limits for LLM calls

## Testing

The batch processor has a comprehensive test suite:

1. Unit tests with mongomock-motor for MongoDB mocking
2. Mock LLM responses for deterministic testing
3. Concurrency tests for race conditions
4. Error handling tests for various failure scenarios

## Usage Examples

### Basic Usage

```python
from batch_processor import BatchProcessor

async def main():
    processor = BatchProcessor()
    stats = await processor.run()
    print(f"Processed {stats['documents_processed']} documents")
```

### CLI Usage

```bash
# Basic usage
python cli.py

# Custom batch size and concurrency
python cli.py --batch-size 20 --max-concurrent 8

# Dry run mode
python cli.py --dry-run
```

### Import Sample Data

```bash
python utils/mongodb_import.py --count 100
```

## Future Enhancements

1. **Retry logic**: Smart retries for failed documents
2. **Priority queues**: Process urgent queries first
3. **Performance monitoring**: Detailed metrics for processing time
4. **Adaptive concurrency**: Adjust based on system load
5. **Filtering**: Process specific subsets of documents