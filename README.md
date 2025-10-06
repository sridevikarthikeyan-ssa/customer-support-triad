
# Customer Support Query Classification System

This project provides two distinct features for classifying customer support queries using Large Language Models (LLMs):

1. **API Server & Client (Real-Time Classification):**
  - A FastAPI-based REST API for real-time classification of customer support conversations.
  - An API client script for sending conversations to the API and collecting results.

2. **Batch Processing Pipeline (MongoDB):**
  - An asynchronous batch processor for classifying large sets of queries stored in MongoDB.
  - Command-line and programmatic interfaces for batch operations.

Each feature is independent and can be used separately. See the relevant section below for setup and usage.

---

# 1. API Server & Client (Real-Time Classification)

## Overview

The API server provides REST endpoints for classifying customer support queries in real time using an LLM. The API client script demonstrates how to send conversations to the server and collect results.

## Setup

1. Install dependencies:
  ```bash
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  ```
2. Set environment variables (copy `.env.example` to `.env` and edit as needed).
3. Start the API server:
  ```bash
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  ```

## API Usage

- POST `/classify` with a conversation payload to receive classification results.

## API Client Example

Run the API client script to classify a batch of conversations via the API:
```bash
python api_client_production.py
```

Results will be saved in the `/data` directory.

---

---

# 2. Batch Processing Pipeline (MongoDB)

## Overview

The batch processing pipeline classifies large sets of customer support queries stored in MongoDB using an LLM. It is designed for asynchronous, high-throughput processing and is independent of the API server.

## Setup

1. Install dependencies (if not already done):
  ```bash
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  ```
2. Set environment variables (see `.env.example`).
3. Ensure MongoDB is running and accessible.

## Usage

You can run the batch processor from the command line or as a Python module.

### Command Line Example (PowerShell)

```powershell
PS C:\> python run_batch_processor.py --batch-size 2 --concurrent 2
```
Replace the numbers as needed for your batch size and concurrency.

### Programmatic Example

See below for usage in Python code.

## Batch Processor Components

The batch processor consists of the following modules:
- `batch_processor.py`: Main batch processing logic
- `cli.py`: Command-line interface for batch processing
- `utils/`: Utility modules for batch management, retries, and concurrency

---



---

## API Client Script: `api_client_production.py`

This script sends a large set of production-grade customer support conversations (e.g., Delta Airlines, Sprintcare) to the running API for classification. It demonstrates end-to-end, multi-turn classification and writes the results to a timestamped file in `/data`.

**How it works:**
- Loads one local hardcoded example and the rest from a large JSON file (e.g., `Delta_Airline_20250916_150358.json`).
- Sends each conversation to the `/classify` API endpoint.
- Collects all successful responses.
- Writes the classified results as a valid JSON array to `/data/classified_results_<UTC>.json`.

**Prerequisites:**
- The API server must be running locally at `http://localhost:8000` (see setup above).
- The relevant data file (e.g., `Delta_Airline_20250916_150358.json`) must be present in the project root.
- Python 3.8+ and the dependencies in `requirements.txt` must be installed.

**Usage:**
1. Ensure the API server is running:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Run the batch client:
   ```bash
   python api_client_production.py
   ```
3. After completion, find the classified results in the `/data` directory as `classified_results_<UTC>.json`.

**Notes:**
- Only successful API responses are saved.
- The script automatically avoids duplicate classification of the hardcoded example.
- Useful for full-scale E2E testing, regression, and production validation.

---


## Batch Processor: `batch_processor.py`

This module provides an asynchronous batch processing system for classifying customer support queries stored in a MongoDB database. It fetches unprocessed queries in batches, classifies them using the LLM wrapper, and stores the results back in MongoDB.

**Features:**
- Asynchronous batch processing with concurrency control
- MongoDB integration for data storage and retrieval
- Configurable batch size and concurrency levels
- Robust error handling and detailed logging
- Processing statistics collection

**MongoDB Schema:**
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

**Usage (Python):**
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

**Command Line Example (PowerShell):**
```powershell
PS C:\> python run_batch_processor.py --batch-size 2 --concurrent 2
```
Replace the numbers as needed for your batch size and concurrency.

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
   
  ```env
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

[Design Document](docs/Design_customer_support_query_classification.md)
[Implementation & Testing Plan](docs/Implementation_and_Testing_Plan.md)
[Software Requirements Specification](docs/SRS_customer_support_query_classification.md)

---

## Environment Variables

All configuration is managed via environment variables in a `.env` file. Key variables include:

- `MONGODB_URI`: MongoDB connection string (e.g., `mongodb://localhost:27017`)
- `MONGODB_DB`: Database name (e.g., `customer_support`)
- `MONGODB_QUERIES_COLLECTION`: Collection for queries (default: `queries`)
- `MONGODB_RESULTS_COLLECTION`: Collection for results (default: `results`)
- `LLM_API_URL`: URL for the LLM endpoint (e.g., `http://localhost:11434/api/generate`)
- `LLM_MODEL`: Name of the LLM model to use (e.g., `llama2`, `mistral`, etc.)
- `LLM_API_KEY`: (If required) API key for LLM provider
- `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`)
- `BATCH_SIZE`: Default batch size for batch processor (overridable via CLI)
- `MAX_CONCURRENT`: Default concurrency for batch processor (overridable via CLI)

See `.env.example` for a full list and descriptions.

## LLM Integration

The system uses a Large Language Model (LLM) for classification. By default, it supports Ollama-compatible endpoints but can be extended for other providers.

- **Model Selection**: Set `LLM_MODEL` in your `.env` to choose the model.
- **Endpoint**: Set `LLM_API_URL` to the LLM's API endpoint.
- **Schema**: The LLM must return a JSON object with `intent`, `topic`, and `sentiment` fields. See `prompt_builder.py` for the expected schema and prompt format.
- **Customization**: To use a different LLM or schema, update `llm_wrapper.py` and `prompt_builder.py` accordingly.

## Error Handling and Logging

All errors are handled via a centralized error handler (`error_handler.py`). Logs are written to the console by default, with log level controlled by the `LOG_LEVEL` environment variable or CLI flag.

- **Log Levels**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Error Format**: API and batch errors are returned in a consistent JSON format (see Error Handling Example above).
- **Custom Logging**: To log to a file or external system, modify `logger.py`.

## Utility Modules

Several utility modules support advanced workflows:

- `utils/batch_file_manager.py`: Manages batch file creation, status (pending/completed/retry), and atomic operations.
- `utils/retry_utils.py`: Handles retry logic for failed batches or API calls.
- `utils/concurrency_check.py`: Ensures safe concurrent processing and prevents race conditions.
- `utils/` (other): Additional helpers for file I/O, statistics, and more.

## Batch File Workflow

The batch processor uses a file-based workflow for tracking processing status:

- **Pending**: New batches are placed in `batch_files/pending/`.
- **Completed**: Successfully processed batches move to `batch_files/completed/`.
- **Retry**: Failed batches are moved to `batch_files/retry/` for later reprocessing.

To retry failed batches, move files from `retry/` back to `pending/` and rerun the processor.

## Testing Details

The test suite covers unit, integration, and end-to-end scenarios:

- **Unit Tests**: Test core logic in isolation (e.g., LLM wrapper, prompt builder, error handler).
- **Integration Tests**: Validate MongoDB and batch processor integration (see `tests/integration_config.py`, `test_mongo_client.py`, etc.).
- **Batch Processor Tests**: Simulate batch processing with various batch sizes and concurrency (see `test_batch_processor.py`).
- **How to Run**:
  ```bash
  pytest tests/
  ```
  Use markers or test file names to run specific tests.

## Extending and Customizing

- **Add New Classification Fields**: Update `prompt_builder.py` and adjust the schema in `llm_wrapper.py` and downstream consumers.
- **Plug in a Different LLM**: Modify `llm_wrapper.py` to support new API protocols or authentication.
- **Customize Batch Logic**: Extend `batch_processor.py` for new workflows, error handling, or statistics.

## Troubleshooting & FAQ

**Q: MongoDB connection fails?**
A: Check `MONGODB_URI` and ensure MongoDB is running. Use `check_mongo_connection.py` for diagnostics.

**Q: LLM API times out or returns errors?**
A: Verify `LLM_API_URL` and model name. Check logs for error details. Increase timeout in `llm_wrapper.py` if needed.

**Q: Schema validation errors?**
A: Ensure the LLM returns the expected JSON structure. See `prompt_builder.py` for the required schema.

**Q: Batch processor skips documents or retries endlessly?**
A: Check the `processed` flag and `processing_attempts` in your queries collection. Review logs for error context.

**Q: How do I reset or reprocess batches?**
A: Move files from `batch_files/retry/` to `batch_files/pending/` and rerun the processor.

For more, see the `docs/` folder and open an issue if you need help.

- [Design Document](docs/Design_customer_support_query_classification.md)
- [Implementation & Testing Plan](docs/Implementation_and_Testing_Plan.md)
- [Software Requirements Specification](docs/SRS_customer_support_query_classification.md)
