## Batch Processing Components

### 1. API Client: `api_client_production.py`

#### What is it?
`api_client_production.py` is a batch client script for sending a large set of production-grade customer support conversations (e.g., Delta Airlines, Sprintcare) to the running API for classification. It demonstrates end-to-end, multi-turn classification and writes the results to a timestamped file in `/data`.

#### How it works
- Loads one local hardcoded example and the rest from a large JSON file (e.g., `Delta_Airline_20250916_150358.json`).
- Sends each conversation to the `/classify` API endpoint.
- Collects all successful responses.
- Writes the classified results as a valid JSON array to `/data/classified_results_<UTC>.json`.

#### Prerequisites
- The API server must be running locally at `http://localhost:8000` (see setup above).
- The relevant data file (e.g., `Delta_Airline_20250916_150358.json`) must be present in the project root.
- Python 3.8+ and the dependencies in `requirements.txt` must be installed.

#### Usage
1. Ensure the API server is running:
  ```bash
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  ```
2. Run the batch client:
  ```bash
  python api_client_production.py
  ```
3. After completion, find the classified results in the `/data` directory as `classified_results_<UTC>.json`.

#### Notes
- Only successful API responses are saved.
- The script automatically avoids duplicate classification of the hardcoded example.
- Useful for full-scale E2E testing, regression, and production validation.

### 2. Batch Processor: `batch_processor.py`

#### What is it?
`batch_processor.py` provides an asynchronous batch processing system for classifying customer support queries stored in a MongoDB database. It fetches unprocessed queries in batches, classifies them using the LLM wrapper, and stores the results back in MongoDB.

#### Features
- Asynchronous batch processing with concurrency control
- MongoDB integration for data storage and retrieval
- Configurable batch size and concurrency levels
- Robust error handling and detailed logging
- Processing statistics collection

#### MongoDB Schema
The batch processor works with two collections:
1. **Queries Collection**:
   ```json
   {
     "_id": "doc0",
     "text": "I can't log into my account after the recent update.",
     "metadata": {
       "source": "email",
       "timestamp": "2025-09-23T10:30:00Z"
     },
     "processed": false,
     "processing_attempts": 0
   }
   ```

2. **Results Collection**:
   ```json
   {
     "query_id": "doc0",
     "classification": {
       "intent": "troubleshooting",
       "topic": "account_access",
       "sentiment": "neutral"
     },
     "processed_at": "2025-09-23T12:45:00Z"
   }
   ```

#### Usage (Python)
```python
from batch_processor import BatchProcessor

async def main():
    processor = BatchProcessor(
        mongodb_uri="mongodb://localhost:27017",
        db_name="customer_support",
        batch_size=10,
        max_concurrent=5
    )
    
    stats = await processor.run()
    print(f"Processed {stats['documents_processed']} documents")
    print(f"Success: {stats['successful']}, Failed: {stats['failed']}")
```

### 3. Command Line Interface: `cli.py`

#### What is it?
`cli.py` provides a command-line interface for running the batch processor with various configuration options.

#### Usage
```bash
# Basic usage with default settings
python cli.py

# Customize batch size and concurrency
python cli.py --batch-size 20 --max-concurrent 8

# Use custom MongoDB connection
python cli.py --mongodb-uri "mongodb://user:pass@host:port" --db-name "my_database"

# Save processing statistics to a file
python cli.py --output "processing_stats.json"

# Dry run mode (fetch but don't process)
python cli.py --dry-run --output "unprocessed_queries.json"

# Set custom logging level
python cli.py --log-level DEBUG
```

#### Available Options
- `--batch-size`: Number of documents to process in each batch (default: 10)
- `--max-concurrent`: Maximum number of concurrent processing tasks (default: 5)
- `--mongodb-uri`: MongoDB connection URI (default: from env or "mongodb://localhost:27017")
- `--db-name`: MongoDB database name (default: from env or "customer_support")
- `--queries-collection`: MongoDB collection for queries (default: "queries")
- `--results-collection`: MongoDB collection for results (default: "results")
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--output`: File path to save processing results (JSON format)
- `--dry-run`: Fetch documents but don't process them

### 4. Demo Script: `utils/demo_batch_processor.py`

#### What is it?
A demonstration script that creates a mock MongoDB environment with sample customer support queries, processes them using the batch processor, and displays the results.

#### Features
- No external MongoDB instance required (uses mongomock)
- Generates sample customer support queries for processing
- Shows full batch processor workflow with mock LLM responses
- Displays processing statistics and classification results

#### Usage
```bash
python utils/demo_batch_processor.py
```

# Customer Support Query Classification API

## Project Overview

This project provides an API for classifying customer support queries using Large Language Models (LLMs). It helps support teams automatically categorize and route incoming queries for faster, more accurate responses. Built with FastAPI, Uvicorn, and Ollama LLM, and containerized with Docker for easy deployment.

## Features

- Multi-turn query classification
- Strict JSON schema validation for LLM responses
- Robust error handling and logging
- Configurable LLM model and endpoint
- RESTful API endpoints for integration
- Asynchronous batch processing with MongoDB integration
- Command-line interface for batch operations
- End-to-end test suite

## Setup (Local)

1. Clone the repo and navigate to `customer-support-triad`.

2. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Set environment variables (copy `.env.example` to `.env` and edit as needed).

4. Start the API server:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Setup (Docker)

1. Build the Docker image:

   ```bash
   docker build -t support-query-api .
   ```

2. Run the container:

   ```bash
   docker run -p 8000:8000 --env-file .env support-query-api
   ```

## API Usage

- POST `/classify`

  - Request body:

    ```json
    {
      "conversation_number": "123",
      "messages": [
        {"sender": "customer", "text": "Where is my order?"},
        {"sender": "agent", "text": "Let me check for you."}
      ]
    }
    ```

  - Response:

    ```json
    {
      "conversation_number": "123",
      "messages": [...],
      "classification": {
        "intent": "...",
        "topic": "...",
        "sentiment": "..."
      }
    }
    ```

## Error Handling Example

All API responses follow a strict schema. Errors are returned in the following format:

```json
{
  "error": {
    "type": "ValidationError",
    "message": "Invalid query format."
  }
}
```

## Testing

- Run unit and integration tests:

  ```bash
  pytest tests/
  ```

- Run performance test:

  ```bash
  python tests/performance_test.py
  ```

## Configuration

- See `.env.example` for required environment variables.
- See `docs/` for design and implementation details.

## MongoDB Setup (for Batch Processor)

For production use with a real MongoDB instance:

1. Install MongoDB:
   ```bash
   # For Ubuntu
   sudo apt update
   sudo apt install -y mongodb-org
   sudo systemctl start mongod
   
   # For macOS
   brew tap mongodb/brew
   brew install mongodb-community
   brew services start mongodb-community
   ```

2. Create database and collections:
   ```bash
   mongosh
   > use customer_support
   > db.createCollection("queries")
   > db.createCollection("results")
   > db.queries.createIndex({ "processed": 1 })
   ```

3. Configure environment variables:
   ```
   MONGODB_URI=mongodb://localhost:27017
   MONGODB_DB=customer_support
   MONGODB_QUERIES_COLLECTION=queries
   MONGODB_RESULTS_COLLECTION=results
   ```

## Contribution Guide

We welcome contributions! To get started:

1. Fork the repository and create a feature branch.
2. Follow the coding standards and add tests for new features.
3. Submit a pull request with a clear description of changes.
4. Ensure all tests pass before requesting review.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For questions or support, please open an issue in the GitHub repository or contact the maintainer.

## Documentation Links

- [Design Document](docs/Design_customer_support_query_classification.md)
- [Implementation & Testing Plan](docs/Implementation_and_Testing_Plan.md)
- [Software Requirements Specification](docs/SRS_customer_support_query_classification.md)
