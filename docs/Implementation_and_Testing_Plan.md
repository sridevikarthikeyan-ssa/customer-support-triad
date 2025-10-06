# Implementation & Testing Plan

## Customer Support Query Classification Module

---

### 1. Overview
This document provides a step-by-step implementation and testing plan for building the customer support query classification module. Each major component is broken down into actionable sub-tasks, with corresponding testing strategies to ensure correctness and reliability.

The implementation consists of two main components:
1. **Real-time API Server**: For processing individual conversation classification requests
2. **MongoDB Batch Processor**: For processing large volumes of conversations asynchronously

---

### 2. Implementation Plan (Sub-Tasks)

#### 2.1. Project Setup
- [ ] Initialize Python package structure in `customer-support-triad`.
- [ ] Create and update `requirements.txt` for dependencies.
- [ ] Set up environment variable management in `config/` (including OLLAMA_MODEL for local model selection).
- [ ] Prepare sample data in `data/`.

#### 2.2. API Layer
- [ ] Implement `api.py` to accept and validate incoming JSON requests.
- [ ] Add error handling for invalid input and content type.
- [ ] Integrate logging for all API interactions.
- [ ] Write unit tests for API input validation and error handling.

#### 2.3. Conversation Aggregator
- [ ] Implement `aggregator.py` to combine all messages for a conversation.
- [ ] Handle edge cases (missing fields, empty messages).
- [ ] Add logging for aggregation steps.
- [ ] Write unit tests for message aggregation logic.

#### 2.4. Prompt Builder
- [ ] Implement `prompt_builder.py` to construct prompts using instructions and samples.
- [ ] Support both few-shot and zero-shot prompting.
- [ ] Add logging for prompt construction.
- [ ] Write unit tests for prompt formatting and sample selection.

#### 2.5. LLM Wrapper
- [ ] Implement `llm_wrapper.py` to connect to Ollama (localhost) and send prompts.
- [ ] Use OLLAMA_MODEL environment variable to select the local model for all LLM calls.
- [ ] Design extensible wrapper for future OpenAI/cloud LLMs.
- [ ] Add error handling for LLM connectivity and timeouts.
- [ ] Add logging for LLM interactions.
- [ ] Write unit tests and integration tests for LLM calls (mocked).

#### 2.6. Classifier
- [ ] Implement `classifier.py` to parse and validate LLM output.
- [ ] Validate output schema (intent, topic, sentiment).
- [ ] Add error handling for parsing failures.
- [ ] Add logging for classification results.
- [ ] Write unit tests for output parsing and schema validation.

#### 2.7. Error Handler
- [ ] Implement `error_handler.py` to format and propagate error responses.
- [ ] Ensure all modules use consistent error handling.
- [ ] Write unit tests for error formatting.

#### 2.8. Logger
- [ ] Implement centralized logging in `logger.py`.
- [ ] Ensure all modules log key events and errors.
- [ ] Write unit tests for logger configuration.

#### 2.9. Integration & End-to-End Testing
- [ ] Write integration tests to validate workflow from API input to LLM output and response.
- [ ] Simulate real-world scenarios and edge cases.
- [ ] Validate error propagation and logging across modules.

#### 2.10. Performance Testing
- [ ] Simulate concurrent requests to ensure support for 10 requests/sec.
- [ ] Measure and log response times.
- [ ] Optimize bottlenecks if needed.

#### 2.11. Async LLM Wrapper
- [ ] Implement `async_llm_wrapper.py` for concurrent LLM calls
- [ ] Use `aiohttp.ClientSession` for asynchronous HTTP requests
- [ ] Add identical function signatures to the synchronous wrapper with async/await pattern
- [ ] Implement timeout and retry control for batch processing workflows
- [ ] Add comprehensive error handling for LLM connection issues
- [ ] Write unit tests for async LLM operations (mocked)

#### 2.12. MongoDB Client
- [ ] Implement `mongo_client.py` for database interaction
- [ ] Configure MongoDB connection URL: `mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT`
- [ ] Set up collection names: `conversation_set` (source) and `sentimental_analysis` (results)
- [ ] Use Motor (async MongoDB driver) with connection pooling
- [ ] Implement cursor-based pagination using ObjectId
- [ ] Configure optimal connection pool parameters (max 20, min 5)
- [ ] Add error handling with exponential backoff retries
- [ ] Write unit tests for MongoDB operations (mocked)

#### 2.13. Batch Processor
- [ ] Implement `batch_processor.py` as the main entry point
- [ ] Configure MongoDB collections: `conversation_set` (source) and `sentimental_analysis` (results)
- [ ] Create professional CLI interface using argparse
- [ ] Implement local file cache for crash recovery
- [ ] Add batch processing modes (one-time, continuous, scheduled)
- [ ] Add monitoring and progress reporting
- [ ] Write unit tests for batch processing workflow

#### 2.14. Batch File Manager
- [ ] Implement local file cache management for batches
- [ ] Create file structure with pending/retry/completed files
- [ ] Add checkpoint system for crash recovery
- [ ] Implement single retry queue with state-aware processing
- [ ] Write unit tests for file operations and recovery scenarios

#### 2.15. Concurrent Processor
- [ ] Implement semaphore-controlled concurrent processing
- [ ] Configure processing modes (conservative, balanced, aggressive)
- [ ] Add immediate write strategy with shared connection pool
- [ ] Implement state-aware retry logic for different failure types
- [ ] Write unit tests for concurrent operations

#### 2.16. Documentation & Deployment
- [ ] Update `README.md` with setup, usage, and API details
- [ ] Add batch processor documentation and command-line examples
- [ ] Document configuration options for both API and batch processor
- [ ] Create environment variable reference documentation
- [ ] Prepare deployment scripts for both components

---

### 3. Testing Plan

#### 3.1. Unit Testing
- Write unit tests for each module in `tests/`.
- Use pytest or unittest for test automation.
- Cover input validation, error handling, and core logic.
- Test both synchronous (API) and asynchronous (batch) components.

#### 3.2. Integration Testing
- Test interactions between API, aggregator, prompt builder, LLM wrapper, and classifier.
- Test batch processor interactions with MongoDB client, async LLM wrapper, and file system.
- Use mocked LLM responses and MongoDB operations for reliability.
- Validate concurrent processing behavior with controlled testing environments.

#### 3.3. End-to-End Testing
- **API Server**: Simulate full workflow from client request to API response.
- **Batch Processor**: Validate end-to-end batch processing from source collection to results.
- Test crash recovery scenarios for batch processor by simulating interruptions.
- Verify proper error handling and recovery across all components.

#### 3.4. Performance Testing
- **API Server**: Use tools like `pytest-benchmark` to simulate concurrent API requests.
- **Batch Processor**: Benchmark different concurrency configurations (3, 5, 10 parallel tasks).
- Measure and compare processing rates with different configurations.
- Validate memory usage and connection pool behavior under load.
- Test performance with varying batch sizes (50, 100, 200) to optimize throughput.

#### 3.5. MongoDB Integration Testing
- Test connection with the specific MongoDB Atlas URL: `mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT`
- Verify correct source collection (`conversation_set`) and results collection (`sentimental_analysis`) usage
- Test connection pooling with different connection parameters
- Validate ObjectId-based pagination and cursor behavior
- Test retry mechanisms for MongoDB operations with simulated failures
- Verify proper database indexing and query performance
- Test crash recovery using local file cache and ObjectId checkpoints

#### 3.6. Async Processing Testing
- Test semaphore-controlled concurrency with different limits.
- Validate state-aware processing of different failure types.
- Measure throughput with varying concurrency settings.
- Test concurrent LLM calls with controlled response times.
- Verify proper error isolation between parallel tasks.

#### 3.7. Manual Testing
- Test edge cases and unusual input formats for both API and batch processor.
- Validate monitoring and progress reporting in different environments.
- Test CLI interface with various command-line arguments and configurations.
- Verify logging and error traces for debugging both components.

---

### 4. Task Tracking & Review
- Track progress using checklists or a project management tool.
- Review code and tests for each sub-task before merging.
- Update documentation as implementation evolves.

---

*End of Implementation & Testing Plan*
