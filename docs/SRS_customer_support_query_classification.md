# Software Requirements Specification (SRS)

## Customer Support Query Classification Module


### 1. Introduction

This document specifies the requirements for a Python module that classifies customer support queries by intent, topic, and sentiment for every customer conversation. The module is designed to be consumed by external services via a first-class API and leverages LLMs for classification.


### 2. High-Level Requirements

1. The module shall be written in Python 3.x.

2. The module shall be well-structured and modularized for maintainability and scalability.

3. The module shall use environment variables for configuration (e.g., OLLAMA_MODEL, OLLAMA_ENDPOINT, API keys, working directory).

4. The module shall include a `requirements.txt` file listing all Python dependencies.

5. The module shall include a `docs` folder for documentation.

6. The module shall include a comprehensive `README.md`.

7. The module shall connect and interact with LLMs to classify each customer conversation, supporting multi-turn (all messages in a conversation).

8. The module shall expose a first-class API for external service consumption.
    - 8.1. The API input shall be in JSON format, following the structure of `sprintcare_20250906_223616.json`.
    - 8.2. The API shall be invoked per `conversation_number`.
    - 8.3. The module shall send all messages in a customer conversation to the LLM for classification (intent, topic, sentiment), supporting multi-turn aggregation.
    - 8.4. The API shall return classification results in JSON format, preserving the incoming structure and adding classification fields. The response must strictly follow the output schema (intent, topic, sentiment) and not include extra keys or commentary.

9. The module shall support two options for LLM context:
    - Option A: Use locally defined instructions and multi-turn few-shot samples.
    - Option B: Use RAG (Retrieval Augmented Generation) for rich context.

10. The module shall support LLM models with streaming enabled or disabled, without affecting API interactions.

11. The module shall support robust error handling and error responses for API calls, validating incoming JSON data and content type. All errors must be returned as standardized error objects.

12. The module shall handle errors from the LLM and respond appropriately to API callers, including robust JSON parsing (extract valid JSON substring if needed).

13. The module shall provide first-class logging for debugging and tracing the workflow, including all aggregation, prompt construction, LLM interaction, and classification steps.

14. The module shall support up to 10 incoming requests per second, mapping each request/response to LLM interactions and logging all traces.

15. The module shall use `.env` and `config/.env.example` for reproducibility and collaboration, and `.gitignore` shall always keep these files and `docs/reports/` tracked.

16. The module shall support MongoDB integration through a standalone batch processing component that operates independently from the real-time API server.
    - 16.1. The module shall include a separate batch processor script for MongoDB-based conversation processing.
    - 16.2. The batch processor shall read conversations from MongoDB source collections and store classified results in destination collections.
    - 16.3. The batch processor shall support multiple execution modes including one-time processing, continuous monitoring, and scheduled operations.
    - 16.4. Both API server and batch processor shall share core classification logic through modular design.



### 3. Functional Requirements

- Accept customer queries in JSON format per conversation.

- Aggregate all messages in a conversation and send to LLM for classification, supporting multi-turn (all messages).

- Return classification results (intent, topic, sentiment) in the same JSON structure with added fields, strictly following the output schema.

- Support both local instructions (with multi-turn few-shot samples) and RAG for LLM context.

- Provide robust error handling and logging in all submodules (aggregator, prompt builder, LLM wrapper, classifier).

- Support streaming and non-streaming LLM models.

- Ensure API performance for up to 10 requests/sec.

- Use robust JSON parsing for LLM responses, extracting valid JSON substring if needed.

- Return standardized error objects for all error cases (input validation, LLM errors, parsing errors).



#### LLM Connectivity Wrapper

- The module shall provide a wrapper for Ollama connectivity, supporting selection of the local Ollama model via the OLLAMA_MODEL environment variable and endpoint via OLLAMA_ENDPOINT.

- The design shall be extensible to support additional wrappers for connecting to OpenAI models (or other cloud-hosted LLMs) using API keys in the future.

- The module shall provide both synchronous and asynchronous LLM wrapper implementations:
  - **Synchronous Wrapper** (`llm_wrapper.py`): Used by the real-time API server for individual request processing
  - **Asynchronous Wrapper** (`async_llm_wrapper.py`): Used by the batch processor for concurrent LLM operations

- The asynchronous LLM wrapper shall implement the following capabilities:
  - Support for 5-10 concurrent LLM calls using `aiohttp.ClientSession`
  - Identical function signatures to the synchronous wrapper with async/await pattern
  - Timeout and retry control for robust operation in batch processing workflows
  - Complete isolation from the synchronous wrapper to ensure zero risk to API operations



### 3.1. MongoDB Database Integration Requirements

The module shall provide MongoDB integration capabilities through a standalone batch processing component that operates independently from the real-time API server, ensuring operational isolation and optimal performance for both real-time and batch processing workflows.

#### 3.1.1. Standalone Batch Processor Architecture

- The module shall include a separate Python script (`batch_processor.py`) for MongoDB-based conversation processing that operates independently from the FastAPI server.

- **ARCHITECTURAL DECISION**: The batch processor shall implement independent classification logic separate from the real-time API to ensure operational isolation and prevent production API disruption.

- The batch processor shall not interfere with or depend on the real-time API server operations, maintaining complete independence for maintenance and deployment.

- The batch processor shall be organized using a flat file structure with `batch_processor.py` and `mongo_client.py` in the root directory alongside existing components.

#### 3.1.2. MongoDB Connection and Configuration

- **ARCHITECTURAL DECISION**: The batch processor shall use Motor (async MongoDB driver) with connection pooling for optimal performance with LLM processing bottlenecks.

- The processor shall implement asynchronous processing architecture using AsyncIO with controlled concurrency (5-10 parallel LLM tasks) managed by semaphore controls.

- The processor shall establish secure connections to MongoDB instances using environment variables for configuration with connection pooling parameters:
  - `maxPoolSize`: 20 connections
  - `minPoolSize`: 5 connections  
  - `maxIdleTimeMS`: 30000ms
  - `serverSelectionTimeoutMS`: 5000ms

- The processor shall support MongoDB authentication mechanisms including connection string authentication, username/password, and certificate-based authentication.

- The processor shall validate MongoDB connectivity and collection accessibility before starting processing operations.

#### 3.1.3. Source Data Processing

- **ARCHITECTURAL DECISION**: The batch processor shall implement local file cache strategy with ObjectId-based cursor pagination for efficient and crash-resistant data processing.

- **Batch File Creation and Management**:
  - The processor shall read unclassified conversations from MongoDB source collections using ObjectId-based cursor pagination
  - Conversations shall be downloaded in configurable batches (default: 100) and saved as local JSON files
  - Each batch file shall contain metadata including `batch_id`, `first_object_id`, `last_object_id`, and `conversation_count`
  - Batch files shall follow naming convention: `batch_XXX_pending.json` where XXX is zero-padded sequence number
  - The processor shall use `_id > last_processed_objectid` queries for efficient continuation after interruptions

- **Local Batch File Schema**:
  - Batch files shall include comprehensive metadata for recovery and tracking
  - ObjectId references shall be preserved as both ObjectId and string formats for compatibility
  - Creation timestamps and conversation counts shall be included for progress monitoring
  - Each batch file shall be self-contained with all necessary conversation data for offline processing

- The processor shall support flexible query filters to select specific conversations for processing based on criteria such as date ranges, processing status, or conversation metadata.

- The processor shall handle large datasets efficiently using MongoDB cursor-based pagination with configurable batch sizes and ObjectId-based continuation.

- **Processing Status Management**:
  - The processor shall track processing status using minimal updates to source collections
  - Status field updates shall include: "pending", "processing", "processed", "failed"
  - The processor shall update `last_processed_at` timestamps for audit and recovery purposes
  - ObjectId checkpointing shall enable precise continuation from interruption points

- The processor shall validate source document schema and handle both legacy message format and production tweet format from MongoDB collections.

- **Crash-Resistant Design**:
  - Local batch files shall survive process crashes and system interruptions
  - The processor shall resume from pending batch files without requiring MongoDB connectivity
  - ObjectId-based continuation shall prevent duplicate processing and ensure data consistency
  - Batch file metadata shall enable precise progress calculation and completion detection

#### 3.1.4. Classification Processing Pipeline

- **ARCHITECTURAL DECISION**: The batch processor shall implement concurrent processing with immediate writes using shared MongoDB connection pools for optimal performance and crash resilience.

- **Asynchronous Concurrent Processing Architecture**:
  - The processor shall implement independent classification logic optimized for async batch processing while maintaining compatibility with existing LLM wrapper and classification components
  - The processor shall process conversations using asynchronous concurrent processing with controlled semaphore limits (5-10 parallel conversations)
  - ThreadPoolExecutor integration shall handle LLM calls to manage the 30-60 second response bottleneck efficiently
  - AsyncIO event loop shall coordinate concurrent operations while maintaining resource limits and system stability

- **Immediate Write Strategy with Connection Protection**:
  - The processor shall write classification results to MongoDB immediately after each individual LLM completion
  - Write operations shall use shared MongoDB connection pool for both source reads and result writes
  - Connection pool configuration shall optimize for concurrent operations with appropriate pool sizing (20 max, 5 min connections)
  - Write time shall be negligible (~10ms) compared to LLM processing time (30-60 seconds), eliminating write bottlenecks

- **Resource Configuration and Concurrency Control**:
  - The processor shall support configurable concurrency levels (3-10 parallel conversations) with resource configuration options:
    - Conservative: 3 concurrent, 50 batch size (low memory, ~4 hours for 1000 conversations)
    - Balanced: 5 concurrent, 100 batch size (medium memory, ~2.5 hours for 1000 conversations)
    - Aggressive: 10 concurrent, 200 batch size (high memory, ~1.25 hours for 1000 conversations)
  - Semaphore controls shall prevent resource exhaustion while maximizing throughput
  - Memory usage shall be optimized through batch processing and controlled concurrency limits

- **Processing Flow with State Management**:
  - Each conversation shall follow: Load → LLM Classification → Immediate MongoDB Write → Progress Update
  - Failed LLM calls shall be queued with status `llm_failed` for complete reprocessing
  - Failed MongoDB writes shall be queued with status `write_failed` preserving classification results for write-only retry
  - Successful operations shall be marked complete immediately with no queuing overhead

- The processor shall provide progress tracking and processing statistics during batch operations with real-time rate calculation and ETA estimation.

- **Error Isolation and Continuity**:
  - Individual conversation failures shall not affect parallel processing of other conversations
  - Failed operations shall be isolated to retry queues while successful operations continue uninterrupted
  - Processing shall continue with remaining conversations even when some conversations fail permanently
  - Comprehensive error logging shall track failure patterns and provide operational insights

#### 3.1.5. Results Storage and Data Schema

- **ARCHITECTURAL DECISION**: The batch processor shall use separate results collection strategy to preserve data integrity and provide comprehensive audit trails.

- The processor shall implement minimal status updates in source collections (`conversations`) and store complete classification results in dedicated results collections (`classified_conversations`).

- The source collection schema updates shall include:
  - `status`: "pending|processing|processed|failed" 
  - `last_processed_at`: ISO 8601 timestamp
  - `result_id`: Reference to detailed results (optional)

- The results collection schema shall include:
  - `conversation_number`: String identifier for cross-reference
  - `source_conversation_id`: ObjectId reference to original conversation
  - `classification`: Complete classification object (intent, topic, sentiment, categorization)
  - `processing_metadata`: Comprehensive processing details including:
    - `processed_at`: Processing timestamp
    - `model_used`: LLM model identifier  
    - `processing_duration_ms`: Processing time in milliseconds
    - `processor_version`: Batch processor version
    - `batch_job_id`: Unique job identifier for tracking
  - `created_at`: Record creation timestamp

- The processor shall implement skip-based duplicate handling strategy to avoid reprocessing conversations unless explicitly requested.

- The processor shall create appropriate database indexes for efficient querying:
  - Source collection: `status`, `conversation_number`, `last_processed_at`
  - Results collection: `conversation_number`, `source_conversation_id`, `processing_metadata.batch_job_id`, classification fields

#### 3.1.6. Processing Modes and Execution Options

- **ARCHITECTURAL DECISION**: The batch processor shall implement professional CLI interface using argparse with comprehensive configuration options and self-documenting help system.

- The processor shall support configuration precedence: CLI arguments (highest) > environment variables > default values (lowest).

- **CLI Interface Requirements**:
  - `--mode`: Processing mode selection (batch|continuous|scheduled)
  - `--batch-size`: Number of conversations per batch (default: 100)
  - `--max-concurrent`: Maximum concurrent LLM processing (default: 5)
  - `--source-collection`: Source MongoDB collection name
  - `--results-collection`: Results MongoDB collection name
  - `--verbose`: Enable detailed console output
  - `--monitoring-mode`: Monitoring configuration (development|production|interactive)
  - `--help`: Comprehensive usage documentation

- **One-time Batch Mode**: Process specific set of conversations with completion reporting and exit, supporting filter criteria and conversation limits.

- **Continuous Monitoring Mode**: Monitor source collections for new unprocessed conversations with configurable polling intervals (default: 60 seconds).

- **Scheduled Processing Mode**: Support integration with system schedulers (cron, Windows Task Scheduler) with timestamped logging and batch job identification.

- The processor shall support graceful shutdown on interrupt signals (SIGINT, SIGTERM) with processing status reporting at termination.

#### 3.1.7. Error Handling and Recovery

- **ARCHITECTURAL DECISION**: The batch processor shall implement local file cache with single retry queue approach for comprehensive error handling and crash recovery.

- **Local File Cache Architecture**:
  - The processor shall download conversations in configurable batches (default: 100) and save as local JSON files
  - Each batch file shall contain metadata including `batch_id`, `first_object_id`, `last_object_id`, and `conversation_count`
  - Batch files shall be named using pattern: `batch_XXX_pending.json`, `batch_XXX_retry_queue.json`, `batch_XXX_completed.json`
  - The processor shall use local files as the primary source of truth for crash recovery operations

- **Single Retry Queue with State Management**:
  - The processor shall implement a single retry queue per batch containing both LLM failures and MongoDB write failures
  - Queue items shall include status field (`llm_failed` or `write_failed`) for state-aware processing
  - Failed LLM calls shall preserve conversation data for complete reprocessing
  - Failed MongoDB writes shall preserve both conversation data and classification results for write-only retry
  - The processor shall support different retry logic based on failure state to prevent redundant LLM processing

- **Connection Protection with Exponential Backoff**:
  - LLM operations shall implement 3 retries with exponential backoff (2s, 4s, 8s delays) and 120-second timeouts
  - MongoDB operations shall implement 3 retries with exponential backoff (1s, 2s, 4s delays) and 20-second timeouts
  - The processor shall add failed operations to retry queue after all automatic retries are exhausted
  - Circuit breaker functionality shall halt processing after 5 consecutive failures with 5-minute recovery timeout

- **Crash Recovery Mechanisms**:
  - The processor shall support resume from pending batch files after process crashes or interruptions
  - Recovery shall query MongoDB results collection to identify already-completed conversations and avoid reprocessing
  - The processor shall process retry queues to resume failed operations with preserved state
  - ObjectId-based continuation shall enable precise resumption from last processed conversation

- **Immediate Write Strategy**:
  - The processor shall write classification results to MongoDB immediately after each LLM completion
  - Write operations shall use shared connection pool for optimal performance (~10ms vs 30-60s LLM processing)
  - Failed writes shall preserve classification results in retry queue to avoid redundant LLM processing
  - The processor shall validate successful writes before marking conversations as completed

- The processor shall provide comprehensive error reporting with classification statistics, failure analysis, and recovery recommendations.

#### 3.1.8. Monitoring and Reporting

- **ARCHITECTURAL DECISION**: The batch processor shall implement hybrid monitoring approach with configurable components for different environments and stakeholders.

- **Multi-Level Monitoring Architecture**:
  - **Console Progress Reporter**: Real-time terminal display with progress bars, success/failure counts, processing rate, and ETA calculations
  - **Structured Logging System**: Detailed file-based logging with timestamps, conversation tracking, and error classification
  - **Progress File System**: JSON/CSV progress tracking for external monitoring and dashboard integration

- **Environment-Specific Monitoring Modes**:
  - **Development Mode**: Console output only for immediate feedback during testing
  - **Production Mode**: Structured logging + progress files for automated monitoring
  - **Interactive Mode**: Console + structured logging for manual monitoring with detailed feedback

- **Progress Reporting Requirements**:
  - Real-time processing statistics: processed/total counts, success rate, current processing rate
  - ETA calculations based on current processing speed and remaining conversations
  - Progress bar visualization with percentage completion indicators
  - Batch job tracking with unique identifiers and processing metadata

- **Structured Logging Specifications**:
  - JSON-formatted log entries with conversation numbers, processing times, error details
  - Comprehensive batch job metadata including start time, configuration, and completion statistics
  - Error classification logging with retry attempts and failure analysis
  - Processing audit trails for compliance and operational review

- **External Monitoring Integration**:
  - Progress file updates every 10 processed conversations for real-time external monitoring
  - JSON progress summaries with job status, completion percentage, performance metrics
  - CSV detailed logs for historical analysis and performance optimization
  - Optional health check endpoints for integration with monitoring dashboards

- The processor shall generate comprehensive processing reports in structured formats (JSON, CSV) with statistics, error summaries, and performance analysis.

#### 3.1.9. Environment Configuration

The following environment variables shall be supported for MongoDB integration:

**Core MongoDB Configuration:**
- `MONGODB_CONNECTION_STRING`: `mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT`
- `MONGODB_DATABASE_NAME`: Target database name for operations  
- `MONGODB_SOURCE_COLLECTION`: `conversation_set` (source collection with unclassified conversations)
- `MONGODB_RESULTS_COLLECTION`: `sentimental_analysis` (target collection for storing classification results)
- `MONGODB_TIMEOUT_MS`: Connection and operation timeout in milliseconds (default: 30000)

**Async Processing Configuration:**
- `MONGODB_MAX_POOL_SIZE`: Maximum connection pool size for concurrent operations (default: 20)
- `MONGODB_MIN_POOL_SIZE`: Minimum connection pool size (default: 5)  
- `MONGODB_MAX_IDLE_TIME_MS`: Maximum idle time for pooled connections (default: 30000)
- `BATCH_MAX_CONCURRENT`: Maximum concurrent LLM processing tasks (default: 5)
- `BATCH_PROCESSING_MODE`: Resource configuration mode (conservative|balanced|aggressive, default: balanced)

**Batch File Management:**
- `MONGODB_BATCH_SIZE`: Number of conversations to process in each local batch file (default: 100)
- `BATCH_FILE_DIRECTORY`: Directory for storing local batch files (default: batch_files)
- `BATCH_CHECKPOINT_INTERVAL`: Conversations between progress checkpoints (default: 50)
- `BATCH_RETRY_MAX_ATTEMPTS`: Maximum retry attempts for failed operations (default: 3)

**Connection Protection and Recovery:**
- `LLM_RETRY_DELAYS`: Comma-separated retry delays for LLM operations (default: "2,4,8")
- `MONGODB_RETRY_DELAYS`: Comma-separated retry delays for MongoDB operations (default: "1,2,4")
- `LLM_TIMEOUT_SECONDS`: Timeout for individual LLM classification calls (default: 120)
- `MONGODB_OPERATION_TIMEOUT_MS`: Timeout for MongoDB read/write operations (default: 20000)

**Monitoring and Execution:**
- `BATCH_PROCESSOR_MODE`: Processing mode selection (batch|continuous|scheduled, default: batch)
- `BATCH_MONITORING_MODE`: Monitoring configuration (development|production|interactive, default: production)
- `BATCH_PROGRESS_UPDATE_INTERVAL`: Conversations between progress file updates (default: 10)

**Legacy Environment Variables (Inherited from Existing System):**
- `OLLAMA_MODEL`: LLM model identifier for classification (default: llama3)
- `OLLAMA_ENDPOINT`: LLM service endpoint (default: http://localhost:11434)

These environment variables provide comprehensive configuration control for all aspects of the enhanced batch processing system including local file management, concurrent processing, connection protection, and monitoring capabilities.

#### 3.1.10. Architectural Decisions Record

The following comprehensive architectural decisions have been made for the MongoDB batch processing system:

**Decisions 1-7: Core Architecture**
1. **File Structure**: Flat organization with `batch_processor.py` and `mongo_client.py` in root directory
2. **Code Sharing**: Separate implementations for batch processor and real-time API (operational isolation)
3. **Technology Stack**: Asynchronous processing with Motor (async MongoDB) and controlled concurrency
4. **CLI Interface**: Professional argparse-based CLI with configuration precedence and help documentation
5. **Data Storage**: Separate results collection strategy preserving data integrity with audit trails
6. **Error Handling**: Intelligent retry with exponential backoff and checkpoint-based recovery
7. **Monitoring**: Hybrid approach with configurable console, logging, and progress file components

**Decisions 8-12: Enhanced Implementation**

8. **Batch File Management & Recovery Strategy**: Local file cache with single retry queue approach
   - **Implementation**: Download conversations in batches of 100, save as local JSON files
   - **File Structure**: `batch_001_pending.json`, `batch_001_retry_queue.json`, `batch_001_completed.json`
   - **Recovery**: Process pending files on restart, retry failed conversations from queue
   - **Rationale**: Simplicity over complex status tracking, crash-resistant local storage

9. **ObjectId Handling & Cursor Strategy**: ObjectId-based cursor pagination with reference preservation
   - **Source Reading**: Use `_id > last_processed_objectid` for efficient cursor-based pagination
   - **Batch Tracking**: Store `first_object_id` and `last_object_id` in each batch file metadata
   - **Target Collection**: New ObjectId for results, preserve original as `source_conversation_id`
   - **Checkpoint**: Save last processed ObjectId for precise crash recovery continuation

10. **Concurrent Processing & Write Strategy**: Immediate writes with shared connection pool
    - **Concurrency**: 5-10 concurrent LLM calls controlled by semaphore limits
    - **Write Strategy**: Immediate write to MongoDB after each individual LLM completion
    - **Connection Pool**: Single MongoDB client/pool for both read and write operations
    - **Performance**: Write time negligible (~10ms vs 30-60s LLM processing bottleneck)

11. **Failure Handling & Queue Strategy**: Single retry queue with state-aware processing
    - **Queue Structure**: Single JSON file per batch containing both LLM and write failures
    - **State Management**: `llm_failed` (retry complete process) vs `write_failed` (retry write only)
    - **Data Preservation**: Save classification work when only MongoDB write fails
    - **Processing Logic**: Different retry strategies based on failure state

12. **Connection Protection & Retry Strategy**: Protected operations with exponential backoff
    - **LLM Protection**: 3 retries with exponential backoff (2s, 4s, 8s delays)
    - **MongoDB Protection**: 3 retries with exponential backoff (1s, 2s, 4s delays)  
    - **Timeout Configuration**: 120s for LLM calls, 20s for MongoDB operations
    - **Queue on Failure**: Add to retry queue after all automatic retries exhausted

13. **Async LLM Wrapper Implementation**: Separate async LLM wrapper for batch processing
    - **New File**: `async_llm_wrapper.py` with async/await pattern for batch processing
    - **Existing Preserved**: Keep `llm_wrapper.py` unchanged for API server
    - **Concurrency Support**: Use `aiohttp.ClientSession` for async HTTP calls
    - **API Compatibility**: Identical function signatures as synchronous wrapper
    - **Rationale**: Zero risk to API server, enable concurrent LLM calls, maintain operational isolation

**Implementation Characteristics**:
- **Zero Data Loss**: All failures captured in local queues that survive crashes
- **Simple Recovery**: Resume processing from local files without complex state reconstruction  
- **Immediate Persistence**: Results saved as soon as LLM processing completes
- **State-Aware Retries**: Don't redo expensive LLM calls if classification already succeeded

These decisions prioritize operational simplicity, crash resilience, performance optimization, and production reliability.



### 4. Non-Functional Requirements

- Written in Python 3.x.

- Modular codebase with clear separation of concerns.

- Secure handling of environment variables and secrets.

- Comprehensive documentation in the `docs` folder.

- High reliability and traceability through logging.

- Scalable to handle increased request rates if needed.

- Strict output schema enforcement in API responses.

- Use of Pydantic models for request/response validation in FastAPI recommended for future versions.

- Explicit type hints in function signatures for clarity and IDE support recommended.



### 5. API Specification

- **Input:** JSON per conversation (see `sprintcare_20250906_223616.json` for reference).

- **Output:** JSON per conversation, with added classification fields. The response must strictly follow the output schema (intent, topic, sentiment) and not include extra keys or commentary. The `model_used` field is removed as per requirements.

- **Error Handling:** Return structured error responses for invalid input, LLM errors, and system failures. All errors must be returned as standardized error objects.

- **Logging:** Log all incoming requests, outgoing responses, and LLM interactions with trace IDs. Log aggregation, prompt construction, and classification steps.



### 6. Deployment & Configuration

- Use environment variables for all configuration, including OLLAMA_MODEL and OLLAMA_ENDPOINT to specify the local model and endpoint.

- Document setup and usage in `README.md` and `docs`.

- Provide `requirements.txt` for dependency management.

- `.env` and `config/.env.example` must be tracked for reproducibility and collaboration. `.gitignore` must always keep these files and `docs/reports/` tracked.



### 7. Extensibility

- Support for additional classification fields or LLM models in future versions.

- Easy integration with external services via API.

---



### 8. Validation & Testing

1. **Functional Testing**

    - Verify that the module correctly classifies customer queries by intent, topic, and sentiment, supporting multi-turn conversations.

    - Test with a variety of input formats and edge cases.

2. **End-to-End Testing**

    - Validate the complete workflow from query ingestion to LLM interaction and response generation, including multi-turn aggregation and strict output schema.

    - Ensure integration with external services via the API.

3. **API Testing**

    - Test the API for correct input/output handling, error responses, and schema validation.

    - Confirm that the API returns the expected classification fields (intent, topic, sentiment) and strictly follows the output schema.

4. **Performance Testing**

    - Simulate and validate the module's ability to handle at least 10 requests per second.

    - Ensure accurate tracing and logging of request-response mapping for all client and LLM interactions.

5. **Robustness Testing**

    - Test LLM response parsing for edge cases, including malformed JSON and extraction of valid JSON substrings.

    - Validate standardized error object responses for all error scenarios.

6. **MongoDB Integration Testing**

    - Validate MongoDB connectivity using Motor async driver with connection pooling configurations and shared connection pool architecture.

    - Test asynchronous batch processing performance with controlled concurrency (5-10 parallel LLM tasks) and immediate write strategy to ensure optimal resource utilization and minimal latency.

    - Verify local file cache functionality including batch file creation, ObjectId-based pagination, and crash recovery from pending batch files without MongoDB dependency.

    - Test single retry queue with state-aware processing to ensure proper handling of both LLM failures (`llm_failed`) and MongoDB write failures (`write_failed`) with appropriate retry logic.

    - Verify data integrity during read-process-write cycles using immediate write strategy with shared connection pools, ensuring no data loss, corruption, or duplicate processing.

    - Test comprehensive error handling and recovery mechanisms including:
      - Connection protection with exponential backoff for both LLM (2s, 4s, 8s) and MongoDB (1s, 2s, 4s) operations
      - Local file cache-based crash recovery and ObjectId-based continuation
      - Single retry queue processing with state preservation for failed operations
      - Circuit breaker functionality and error threshold monitoring

    - Validate CLI interface functionality with argparse implementation, testing all configuration options, help documentation, and configuration precedence (CLI > env vars > defaults).

    - Test hybrid monitoring system components (console, structured logging, progress files) across different environment modes (development, production, interactive) with real-time progress tracking.

    - Ensure proper database indexing and query performance optimization for ObjectId-based cursor pagination and efficient conversation retrieval.

    - Test batch file management including creation from MongoDB cursors, local storage, and processing continuation across system restarts.

    - Validate immediate write strategy performance characteristics ensuring MongoDB write operations (~10ms) do not create bottlenecks compared to LLM processing (30-60s).

    - Verify batch processor independence from API server operations and separate implementation isolation to ensure no production API disruption during batch processing operations.

    - Test comprehensive failure scenarios including network outages, LLM service interruptions, MongoDB connection losses, and process crashes to validate zero data loss guarantees.

## End of Specification
