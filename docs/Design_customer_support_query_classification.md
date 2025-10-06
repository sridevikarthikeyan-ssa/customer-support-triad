# Design & Architecture Document

## Implementation Review Summary (2025-10-06)

This section summarizes the actual implementation as of October 2025, based on a comprehensive review of all source, utility, and test code. It clarifies how the codebase realizes the design, highlights architectural patterns, and documents integration points and test coverage.

### Core Modules
- **API Layer (`main.py`, `api.py`)**: FastAPI server with `/classify` endpoint, uses synchronous LLM wrapper, aggregation, prompt building, and classification modules. Robust input validation and error handling.
- **Batch Processor (`batch_processor.py`, `cli.py`)**: Asynchronous batch processing of MongoDB documents, checkpointing, retry logic, batch file management, CLI interface. Uses async LLM wrapper, aggregation, prompt building, and classification.
- **LLM Wrappers (`llm_wrapper.py`, `async_llm_wrapper.py`)**: Sync (API) and async (batch) wrappers for LLM calls, robust error handling, JSON parsing, retry logic.
- **MongoDB Client (`mongo_client.py`)**: Async client, index management, fetch/update/store operations, retry logic.
- **Aggregation & Classification (`aggregator.py`, `classifier.py`)**: Aggregates conversation messages, parses and validates LLM output.
- **Prompt Builder (`prompt_builder.py`)**: Constructs strict prompts with few-shot examples for LLM.
- **Error Handling & Logging (`error_handler.py`, `logger.py`)**: Centralized error formatting and logging.

### Utility Modules
- **Retry Logic (`utils/retry_utils.py`)**: Exponential backoff, error classification, async decorator.
- **Batch File Management (`utils/batch_file_manager.py`)**: Handles batch files, retry queues, checkpoints.
- **Demo/Benchmark/Data Import**: Scripts for demoing with mock MongoDB, benchmarking LLM concurrency, importing sample data.
- **Other Utilities**: Prompt formatting, concurrency checks, CLI wrappers.

### Test Coverage
- **Extensive pytest-based tests** for all major modules: retry logic, prompt builder, MongoDB client, logger, LLM wrappers, error handler, classifier, batch processor, batch file manager.
- **Mocks** for LLM and MongoDB ensure isolated, robust testing of error and edge cases.

### Architectural Patterns & Integration
- **Separation of concerns**: API, batch, and utility layers are modular and loosely coupled.
- **Shared logic**: Aggregation, prompt building, classification, error handling reused across API and batch.
- **Resilience**: Batch processing is robust with checkpointing, retries, and local file management.
- **Testability**: High test coverage, use of mocks, and clear separation of I/O and logic.

---


## Customer Support Query Classification Module (Phase 1)

---

### 1. Detailed Architecture Diagram
#
# Environment & Model Selection
# Only OLLAMA hosted local models are supported for LLM classification.
# The environment variable `OLLAMA_MODEL` must be set to specify which local Ollama model to use (e.g., llama3).
# The endpoint for Ollama should be configured via `OLLAMA_ENDPOINT` (default: http://localhost:11434).



### 2. Segregation: Client-Side vs Model-Side Interactions

```text
┌─────────────────────────────┐
│ 1. Client Request (JSON)    │
└─────────────┬───────────────┘
              │
┌─────────────────────────────┐
│   - Validates input         │
│   - Logs request            │
│   - Error handling          │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 3. Conversation Aggregator  │
│   - Combines messages (multi-turn support) │
│   - Aggregates all customer/agent messages for context │
│   - Logs aggregation        │
│   - Error handling          │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 4. Prompt Construction      │
│   - Uses strict instructions and multi-turn few-shot samples │
│   - Enforces output schema (intent, topic, sentiment) │
│   - Sentiment judged ONLY from customer messages │
│   - Logs prompt             │
│   - Error handling          │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 5. LLM Wrapper (Model Side) │
│   - Sends prompt to LLM     │
│   - Receives response       │
│   - Robust JSON parsing (extracts valid JSON substring if needed) │
│   - Logs LLM interaction    │
│   - Error handling          │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 6. Classifier (Model Side)  │
│   - Parses LLM output       │
│   - Validates schema (intent, topic, sentiment required) │
│   - Returns standardized error object on failure │
│   - Logs classification     │
│   - Error handling          │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 7. API Response (Client Side)│
│   - Returns JSON with       │
│     classification         │
│   - Always includes all messages (multi-turn) │
│   - Logs response           │
│   - Error handling          │
└─────────────────────────────┘
```

---

### 2. Logging and Error Handling in Submodules

- **Conversation Aggregator**: Logs aggregation steps, supports multi-turn, handles errors in message format or missing data.
- **Prompt Construction**: Logs prompt details, enforces strict schema, handles errors in template or sample selection.
- **LLM Wrapper**: Robust JSON parsing, extracts valid JSON substring if needed, logs LLM interaction, handles connectivity and parsing errors.
- **Classifier**: Validates schema, returns standardized error object on failure, logs classification.
---



### 3. API Layer

```python
def classify_conversation(request_json: dict) -> dict:
  logger.info(f"Received request: {request_json}")
  # Validate input schema (must include conversation_number and messages as list)
  if not isinstance(request_json, dict) or "conversation_number" not in request_json or "messages" not in request_json:
    logger.error("Invalid input schema")
    return error_response("Invalid input schema")
  # Pass to aggregator for multi-turn aggregation
  agg_result = aggregate_conversation(request_json)
  if "error" in agg_result:
    return agg_result
  # Build prompt and classify
  prompt_result = build_prompt(request_json["conversation_number"], agg_result["aggregated_text"])
  if "error" in prompt_result:
    return prompt_result
  messages = prompt_result["messages"]
  llm_response = ollama_classify(messages)
  classification = parse_classification(llm_response)
  return build_response(request_json["conversation_number"], request_json["messages"], classification)
```

*Explanation*: Handles request validation, logging, multi-turn aggregation, prompt building, LLM call, and response formatting.




### 4. Conversation Aggregator

```python
def aggregate_conversation(request_json: dict) -> dict:
  try:
    messages = request_json.get("messages", [])
    if not isinstance(messages, list) or len(messages) == 0:
      logger.error("Messages must be a non-empty list")
      return error_response("Messages must be a non-empty list")
    aggregated_text = " ".join([msg["text"] for msg in messages if "text" in msg])
    logger.info(f"Aggregated messages: {aggregated_text}")
    return {
      "conversation_number": request_json.get("conversation_number"),
      "aggregated_text": aggregated_text,
      "messages": messages
    }
  except Exception as e:
    logger.error(f"Aggregation error: {str(e)}")
    return error_response("Aggregation error")
```

*Explanation*: Aggregates all customer/agent messages for multi-turn support, logs aggregation, handles missing data.



```python
def build_prompt(conversation_number: str, aggregated_text: str) -> dict:
  try:
    SYSTEM_PROMPT = (
      "You are a highly accurate customer-support query classifier.\n"
      "Use the entire conversation context for intent and topic.\n"
      "Sentiment must be judged ONLY from the customer's messages.\n"
      "Return a SINGLE JSON object with only the required keys: categorization, intent, topic, sentiment.\n"
      "No extra keys, no explanations, no commentary."
    )
    messages = [
      {"role": "system", "content": SYSTEM_PROMPT}
    ]
    # Add multi-turn few-shot examples
    for ex in FEW_SHOTS:
      user_msgs = []
      for msg in ex["messages"]:
        user_msgs.append(f"{msg['sender'].capitalize()}: {msg['text']}")
      user_content = "\n".join(user_msgs)
      messages.append({"role": "user", "content": user_content})
      messages.append({"role": "assistant", "content": json.dumps(ex["output"], ensure_ascii=False)})
    # Add actual conversation
    user_query = f"Customer Query:\n{aggregated_text}\nReturn ONLY JSON:"
    messages.append({"role": "user", "content": user_query})
    return {"messages": messages}
  except Exception as e:
    logger.error(f"Prompt construction error: {str(e)}")
    return error_response("Prompt construction error")
```

*Explanation*: Builds strict prompt with multi-turn few-shot examples, enforces output schema, logs prompt, handles template errors.




### 5. LLM Wrapper

```python
def ollama_classify(messages: list) -> dict:
  try:
    payload = {
      "model": os.getenv("OLLAMA_MODEL"),
      "messages": messages,
      "options": {"num_predict": 700},
      "stream": False
    }
    response = requests.post(os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434") + "/api/chat", json=payload)
    response.raise_for_status()
    data = response.json()
    content = ""
    if "message" in data:
      content = data["message"].get("content", "").strip()
    elif "messages" in data and len(data["messages"]) > 0:
      content = data["messages"][0].get("content", "").strip()
    if not content:
      logger.error("Empty LLM response content")
      return error_response("Empty LLM response content")
    try:
      parsed = json.loads(content)
      logger.info(f"Extracted JSON object: {parsed}")
      return parsed
    except Exception as e:
      logger.error(f"Failed to parse LLM response content as JSON: {e}")
      # Try to extract JSON substring
      start, end = content.find("{"), content.rfind("}")
      if start != -1 and end != -1:
        try:
          parsed = json.loads(content[start:end+1])
          logger.info(f"Extracted JSON substring: {parsed}")
          return parsed
        except Exception as e2:
          logger.error(f"Failed to parse JSON substring: {e2}")
      return error_response("Failed to parse LLM response as JSON")
  except requests.exceptions.Timeout:
    logger.error("LLM request timed out")
    return error_response("LLM request timed out")
  except requests.exceptions.RequestException as e:
    logger.error(f"LLM connectivity error: {str(e)}")
    return error_response("LLM connectivity error")
  except Exception as e:
    logger.error(f"LLM error: {str(e)}")
    return error_response("LLM error")
```

*Explanation*: Sends prompt to LLM, robustly parses JSON (including substring extraction), logs interaction, handles LLM and parsing errors.




### 6. Classifier

```python
def parse_classification(response: dict) -> dict:
  try:
    # Accepts dict or JSON string
    if isinstance(response, str):
      classification = json.loads(response)
    elif isinstance(response, dict):
      classification = response
    else:
      logger.error("Invalid response type")
      return error_response("Invalid response type")
    required_fields = ["intent", "topic", "sentiment"]
    class_obj = classification.get("classification", classification)
    for field in required_fields:
      if field not in class_obj:
        logger.error(f"Missing field in classification: {field}")
        return error_response(f"Missing field in classification: {field}")
    logger.info(f"Classification parsed: {class_obj}")
    return class_obj
  except json.JSONDecodeError:
    logger.error("Failed to parse LLM response as JSON")
    return error_response("Failed to parse LLM response as JSON")
  except Exception as e:
    logger.error(f"Parsing error: {str(e)}")
    return error_response("Parsing error")
```

*Explanation*: Parses LLM output, validates required fields, returns standardized error object, logs result, handles parsing errors.




### 7. API Response

```python
def build_response(conversation_number: str, messages: list, classification: dict) -> dict:
  try:
    response = {
      "conversation_number": conversation_number,
      "messages": messages,  # Always includes all multi-turn messages
      "classification": classification
    }
    logger.info(f"Response: {response}")
    return response
  except Exception as e:
    logger.error(f"Response error: {str(e)}")
    return error_response("Response error")
```

*Explanation*: Formats final response, always includes all multi-turn messages, logs output, handles formatting errors.

---




### 8. Instructions

- "Classify the following customer support conversation by intent, topic, and sentiment."
- "Use the entire conversation context for classification."
- "Sentiment must be judged ONLY from the customer's messages. Ignore agent tone."
- "Return a SINGLE JSON object with only the required keys: categorization, intent, topic, sentiment."
- "No extra keys, no explanations, no commentary."



### 9. Few-Shot Samples (Multi-Turn)

```json
{
  "messages": [
    {"sender": "customer", "text": "Where is my order?"},
    {"sender": "agent", "text": "Let me check for you."},
    {"sender": "customer", "text": "Can you expedite shipping?"},
    {"sender": "agent", "text": "I have requested expedited shipping."}
  ],
  "classification": {
    "intent": "Order Status",
    "topic": "Shipping/Delivery",
    "sentiment": "Negative"
  }
}
```
---

### 6. Environment Configuration & .gitignore Policy

- `.env` and `config/.env.example` are tracked for reproducibility and collaboration.
- Required environment variables: `OLLAMA_MODEL`, `OLLAMA_ENDPOINT`.
- `.gitignore` is configured to always keep `.env`, `config/.env.example`, and `docs/reports/` tracked.

---

### 7. Testing & E2E Validation

- `api_client.py` includes multi-turn test cases for edge case validation.
- `tests/` directory covers unit and integration tests for all major modules.

---

### 8. Recommendations for Future Improvements

- Use Pydantic models for request/response validation in FastAPI for stricter schema enforcement.
- Add more explicit type hints to function signatures for clarity and IDE support.

---

### 5. Response JSON Schema (API Response)

### 10. Response JSON Schema (API Response)

#### Schema

```json
{
  "conversation_number": "<string>",
  "messages": [
    {"sender": "<string>", "timestamp": "<ISO8601>", "text": "<string>"}
  ],
  "classification": {
    "intent": "<string>",
    "topic": "<string>",
    "sentiment": "<string>",
    // model_used field removed as per requirements
  }
}
```


#### Explanation

- `classification`: Object containing intent, topic, and sentiment for classification.


---

## MongoDB Batch Processing Architecture (Phase 2)

### 1. MongoDB Integration Overview

The MongoDB batch processing system extends the existing real-time API with standalone batch processing capabilities for large-scale conversation classification. This system processes conversations stored in MongoDB collections and outputs classified results to separate collections.

#### Key Design Principles

- **Isolation**: Batch processor operates independently from the real-time API
- **Performance**: Asynchronous processing with controlled concurrency for LLM bottlenecks
- **Data Integrity**: Separate collections preserve original data while maintaining audit trails
- **Robustness**: Comprehensive error handling with intelligent retry mechanisms
- **Monitoring**: Multi-level progress reporting for different environments

---

### 2. Architectural Decisions Summary

#### Decision 1: File Structure & Organization

**CHOSEN: Flat Structure (Simple)**

- All MongoDB-related files in root directory alongside existing files
- Files: `batch_processor.py`, `mongo_client.py`
- Rationale: Maintains consistency with current project structure, easier navigation

#### Decision 2: Code Sharing Strategy

**CHOSEN: Separate Implementations (Isolation)**

- Independent batch processor with its own classification logic
- Existing API server (`main.py`, `api.py`) remains completely unchanged
- Rationale: Operational isolation, no risk to production API, easier maintenance

#### Decision 3: MongoDB Connection & Batch Processing Strategy

**CHOSEN: Asynchronous with Controlled Concurrency**

- **Technology**: Motor (async MongoDB driver) with connection pooling
- **Concurrency**: 5-10 parallel LLM processing tasks controlled by semaphore
- **Performance**: 8-10x faster than sequential (1.25 hours vs 12.5 hours for 1000 conversations)
- **Architecture**: AsyncIO + ThreadPoolExecutor for LLM calls
- Rationale: LLM processing (30-60 seconds) is the bottleneck, not MongoDB operations

#### Decision 4: CLI Interface & Execution Options

**CHOSEN: CLI with Arguments (argparse)**

- Professional CLI tool with `--help` documentation
- Configuration precedence: CLI args > environment variables > defaults
- Support for batch, continuous, and scheduled processing modes
- Rationale: Runtime flexibility, automation-friendly, self-documenting

#### Decision 5: Results Schema & Data Storage Strategy

**CHOSEN: Separate Results Collection**

- Source collection: Minimal status updates only
- Results collection: Dedicated `classified_conversations` with full audit trail
- Duplicate handling: Skip strategy (avoid reprocessing unless explicit)
- Rationale: Data integrity, audit capability, schema flexibility, production safety

#### Decision 6: Error Handling & Recovery Strategy

**CHOSEN: Retry with Backoff + Checkpoints**

- Intelligent error classification (transient, permanent, resource)
- Exponential backoff with jitter (2s-60s delay range)
- Checkpoint system (save progress every 50 conversations)
- Maximum 3 retries for transient errors
- Rationale: Production-ready robustness with efficient recovery

#### Decision 7: Monitoring & Progress Reporting

**CHOSEN: Hybrid Approach (Console + Logs + Files)**

- Configurable monitoring modes (development, production, interactive)
- Real-time console progress + structured logging + JSON/CSV progress files
- External monitoring capability through progress files
- Rationale: Comprehensive flexibility for different environments and stakeholders

#### Decision 8: Batch File Management & Recovery Strategy

**CHOSEN: Local File Cache with Single Retry Queue**

**Options Considered:**
1. **Hybrid Status Tracking** (MongoDB status + checkpoints)
2. **Local File Cache with Single Queue** ✅ **CHOSEN**
3. **Local File Cache with Multiple Queues**

**Implementation:**
- **Batch Creation**: Download conversations in batches of 100, save as local JSON files
- **File Structure**: `batch_001_pending.json`, `batch_001_retry_queue.json`, `batch_001_completed.json`
- **Recovery**: Process pending files on restart, retry failed conversations from queue

**Rationale:**
- **Simplicity**: Much simpler than complex status tracking
- **Crash Recovery**: Local files survive crashes, no network dependency
- **Trade-off**: May reprocess up to 100 conversations after crash vs complex tracking

#### Decision 9: ObjectId Handling & Cursor Strategy

**CHOSEN: ObjectId-Based Cursor Pagination with Reference Preservation**

**Implementation:**
- **Source Reading**: Use `_id > last_processed_objectid` for cursor-based pagination
- **Batch Tracking**: Store `first_object_id` and `last_object_id` in each batch file
- **Target Collection**: New ObjectId for results, preserve original as `source_conversation_id`
- **Checkpoint**: Save last processed ObjectId for crash recovery

**File Structure:**
```json
{
    "batch_id": "batch_001",
    "first_object_id": "66f2a1b0c8d4e5f6a7b8c9c0",
    "last_object_id": "66f2a1b5c8d4e5f6a7b8c9d0",
    "conversations": [...]
}
```

**Rationale:**
- **Efficient Pagination**: ObjectId natural ordering for continuation
- **Reference Integrity**: Maintain relationship between source and results
- **Crash Recovery**: Resume from exact ObjectId position

#### Decision 10: Concurrent Processing & Write Strategy

**CHOSEN: Immediate Writes with Shared Connection Pool**

**Implementation:**
- **Concurrency**: 5-10 concurrent LLM calls (semaphore-controlled)
- **Write Strategy**: Immediate write to MongoDB after each LLM completion
- **Connection Pool**: Single MongoDB client/pool for both reads and writes
- **Performance**: Write time negligible (~10ms vs 30-60s LLM calls)

**Processing Flow:**
```
5 Concurrent LLM Calls → Immediate Individual Writes → Continue Next 5
```

**Rationale:**
- **No Write Bottleneck**: MongoDB writes are instant compared to LLM processing
- **Immediate Persistence**: Results saved as soon as available
- **Simple Recovery**: Query results collection to see what's completed

#### Decision 11: Failure Handling & Queue Strategy

**CHOSEN: Single Retry Queue with State-Aware Processing**

**Options Considered:**
1. **Multiple Queue Files** (LLM failures + Write failures separate)
2. **Single Queue with States** ✅ **CHOSEN**

**Queue Structure:**
```json
[
    {
        "conversation_id": "conv_001",
        "status": "llm_failed",
        "classification_result": null,
        "conversation_data": {...},
        "retry_count": 1
    },
    {
        "conversation_id": "conv_002", 
        "status": "write_failed",
        "classification_result": {...},
        "conversation_data": {...},
        "retry_count": 0
    }
]
```

**State-Aware Processing:**
- **LLM Failed**: Retry complete process (LLM + Write)
- **Write Failed**: Only retry MongoDB write (preserve classification)

**Rationale:**
- **Simplicity**: One queue file vs multiple files
- **Efficiency**: No wasted work (don't redo LLM if already classified)
- **Data Preservation**: Save classification work when only write fails

#### Decision 12: Connection Protection & Retry Strategy

**CHOSEN: Protected Operations with Exponential Backoff**

**Implementation:**
- **LLM Protection**: 3 retries with exponential backoff (2s, 4s, 8s)
- **MongoDB Protection**: 3 retries with exponential backoff (1s, 2s, 4s)
- **Timeout Configuration**: 120s for LLM calls, 20s for MongoDB operations
- **Queue on Failure**: Add to retry queue after all retries exhausted

**Protection Layers:**
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
async def safe_llm_call()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))  
async def safe_mongodb_write()
```

**Rationale:**
- **Zero Data Loss**: All failures captured in queues
- **Automatic Recovery**: Transient failures handled automatically
- **Production Ready**: Robust against network issues and service outages

#### Decision 13: Async LLM Wrapper Implementation

**CHOSEN: Separate Async LLM Wrapper for Batch Processing**

**Options Considered:**
1. **Modify Existing LLM Wrapper** (Break sync API compatibility)
2. **Create Async LLM Wrapper** ✅ **CHOSEN**

**Implementation:**
- **New File**: `async_llm_wrapper.py` with async/await pattern
- **Existing Preserved**: Keep `llm_wrapper.py` unchanged for API server
- **Concurrency Support**: Use `aiohttp.ClientSession` for async HTTP calls
- **API Compatibility**: Identical function signatures, just async versions

**Code Structure:**
```python
# async_llm_wrapper.py
import aiohttp
import asyncio

async def ollama_classify_async(conversation_text, prompt, timeout=120):
    async with aiohttp.ClientSession() as session:
        async with session.post(ollama_url, json=payload, timeout=timeout) as response:
            return await response.json()
```

**Rationale:**
- **Zero Risk**: Existing API server (`main.py`, `api.py`) remains completely unchanged
- **Concurrency**: Enable 5-10 parallel LLM calls for batch processing
- **Maintenance**: Two focused components vs one complex hybrid solution
- **Production Safety**: No impact on proven, stable API functionality

---

### 3. Enhanced MongoDB Batch Processing Architecture

Based on comprehensive design discussions, the MongoDB batch processing system has been enhanced with a local file cache approach that provides superior crash recovery and simplified operational management.

#### 3.1 Local File Cache Implementation

The batch processing system uses local JSON files as the primary mechanism for batch management and crash recovery:

```
batch_files/
├── batch_001_pending.json      ← 100 conversations from MongoDB
├── batch_001_retry_queue.json  ← Single queue for all failures  
├── batch_001_completed.json    ← Completed batch marker
├── batch_002_pending.json      ← Next batch
└── batch_003_pending.json      ← Future batch
```

#### 3.2 Batch File Structure

Each batch file contains conversations with metadata for recovery:

```json
{
    "batch_id": "batch_001",
    "created_at": "2025-09-24T14:30:22Z",
    "first_object_id": "66f2a1b0c8d4e5f6a7b8c9c0",
    "last_object_id": "66f2a1b5c8d4e5f6a7b8c9d0",
    "conversation_count": 100,
    "conversations": [
        {
            "_id": "66f2a1b0c8d4e5f6a7b8c9c0",
            "conversation_data": {...},
            "created_at": "2025-09-24T10:30:00Z"
        }
    ]
}
```

#### 3.3 Single Retry Queue with State Management

The retry queue handles both LLM failures and MongoDB write failures with state-aware processing:

```json
[
    {
        "conversation_id": "66f2a1b5c8d4e5f6a7b8c9d0",
        "status": "llm_failed",
        "classification_result": null,
        "conversation_data": {...},
        "retry_count": 1,
        "failed_at": "2025-09-24T15:22:15Z"
    },
    {
        "conversation_id": "66f2a1b6c8d4e5f6a7b8c9d1",
        "status": "write_failed", 
        "classification_result": {
            "intent": "Complaint",
            "topic": "Service Quality",
            "sentiment": "Negative"
        },
        "conversation_data": {...},
        "retry_count": 0,
        "failed_at": "2025-09-24T15:25:32Z"
    }
]
```

#### 3.4 Immediate Write Strategy with Connection Protection

Each LLM completion triggers an immediate write to MongoDB using shared connection pools:

```python
async def process_conversation_with_immediate_write(conv, semaphore):
    """Process single conversation with immediate persistence"""
    
    async with semaphore:  # Control concurrency
        try:
            # LLM Classification (30-60 seconds)
            classification = await classify_conversation_llm(conv)
            
            # Immediate MongoDB Write (~10ms)
            result_doc = {
                "_id": ObjectId(),
                "source_conversation_id": conv["_id"],
                "classification": classification,
                "original_conversation": conv["conversation_data"],
                "processed_at": datetime.utcnow()
            }
            
            await mongo_client.results_collection.insert_one(result_doc)
            return {"status": "success"}
            
        except LLMError as e:
            await add_to_retry_queue(conv, "llm_failed", str(e))
        except MongoError as e:
            await add_to_retry_queue(conv, "write_failed", str(e), classification)
```

#### 3.5 Crash Recovery Mechanisms

The system provides multiple layers of crash recovery:

1. **Local File Survival**: Batch files survive process crashes
2. **MongoDB Query Recovery**: Check results collection for completed conversations
3. **Retry Queue Processing**: Resume failed operations with preserved state
4. **ObjectId Continuation**: Resume reading from last processed ObjectId

```python
async def recover_from_crash():
    """Complete crash recovery process"""
    
    # Find pending batch files
    pending_files = glob("batch_files/*_pending.json")
    
    for batch_file in pending_files:
        # Check what's already completed in MongoDB
        completed_ids = await get_completed_conversation_ids(batch_file)
        
        # Process retry queue for this batch
        await process_retry_queue(batch_file)
        
        # Continue with remaining conversations
        remaining = await get_unprocessed_conversations(batch_file, completed_ids)
        if remaining:
            await process_conversations(remaining, batch_file)
```

---

### 4. MongoDB Data Architecture

#### Source Collection Schema (`conversation_set`)
```json
{
  "_id": ObjectId("..."),
  "conversation_number": "1",
  "tweets": [
    {
      "tweet_id": 8,
      "author_id": "115712",
      "inbound": true,
      "created_at": "Tue Oct 31 21:45:10 +0000 2017",
      "text": "@sprintcare is the worst customer service"
    }
  ],
  "status": "pending|processing|processed|failed",
  "last_processed_at": "2025-09-24T10:30:00Z"
}
```

#### Results Collection Schema (`sentimental_analysis`)
```json
{
  "_id": ObjectId("..."),
  "conversation_number": "1",
  "source_conversation_id": ObjectId("..."),
  "classification": {
    "intent": "Complaint",
    "topic": "Account/Billing",
    "sentiment": "Negative",
    "categorization": "Requesting refund and sharing negative experience"
  },
  "processing_metadata": {
    "processed_at": "2025-09-24T10:30:00Z",
    "model_used": "llama3",
    "processing_duration_ms": 45000,
    "processor_version": "1.0.0",
    "batch_job_id": "batch_20250924_103000"
  },
  "created_at": "2025-09-24T10:30:00Z"
}
```

---

### 4. Asynchronous Processing Architecture

#### Core Processing Flow
```python
class BatchProcessor:
    def __init__(self, max_concurrent=5):
        # MongoDB connection with pooling
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            connection_string,
            maxPoolSize=20,
            minPoolSize=5,
            maxIdleTimeMS=30000,
            serverSelectionTimeoutMS=5000
        )
        self.max_concurrent = max_concurrent
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
    
    async def process_batch(self, batch_size=100):
        # 1. Read conversations from MongoDB (fast - milliseconds)
        conversations = await self.read_conversations(batch_size)
        
        # 2. Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 3. Process conversations concurrently
        tasks = [
            self.process_single_conversation(conv, semaphore) 
            for conv in conversations
        ]
        
        # 4. Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 5. Batch write results to MongoDB (fast - milliseconds)
        await self.write_results(results)
```

#### Performance Characteristics
- **Sequential Processing**: 1000 conversations × 45 seconds = 12.5 hours
- **5 Concurrent Tasks**: 200 batches × 45 seconds = 2.5 hours  
- **10 Concurrent Tasks**: 100 batches × 45 seconds = 1.25 hours

#### Resource Configuration Options
```python
BATCH_CONFIGS = {
    "conservative": {
        "max_concurrent": 3,
        "batch_size": 50,
        "memory_usage": "Low"
    },
    "balanced": {
        "max_concurrent": 5,
        "batch_size": 100,
        "memory_usage": "Medium"
    },
    "aggressive": {
        "max_concurrent": 10,
        "batch_size": 200,
        "memory_usage": "High"
    }
}
```

---

### 5. Error Handling & Recovery System

#### Error Classification Matrix
```python
ERROR_PATTERNS = {
    ErrorType.TRANSIENT: [
        "connection timeout", "network error", "temporary unavailable",
        "service temporarily unavailable", "rate limit exceeded"
    ],
    ErrorType.PERMANENT: [
        "invalid json", "malformed data", "authentication failed",
        "permission denied", "invalid conversation format"
    ],
    ErrorType.RESOURCE: [
        "out of memory", "disk full", "cpu limit", "too many requests"
    ]
}
```

#### Retry Configuration
```python
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 2.0,          # 2 seconds initial delay
    "max_delay": 60.0,          # 1 minute maximum
    "exponential_base": 2.0,
    "jitter": True,             # Randomize delay ±50%
    "checkpoint_interval": 50    # Save progress every 50 conversations
}
```

#### Circuit Breaker Implementation
```python
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,      # Open circuit after 5 consecutive failures
    "recovery_timeout": 300,     # Try again after 5 minutes
    "error_threshold": 0.1       # Stop if >10% failure rate
}
```

---

### 6. CLI Interface Design

#### Command Structure
```bash
# Basic usage with defaults
python batch_processor.py

# Custom configuration
python batch_processor.py --batch-size 200 --max-concurrent 10 --verbose

# Processing modes
python batch_processor.py --mode continuous --poll-interval 30
python batch_processor.py --mode batch --limit 1000

# Monitoring configuration  
python batch_processor.py --monitoring-mode production
python batch_processor.py --console --logs --progress-files

# Help and documentation
python batch_processor.py --help
```

#### Configuration Precedence
1. **CLI Arguments** (highest priority)
2. **Environment Variables** 
3. **Default Values** (lowest priority)

#### Environment Variables
```bash
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT
MONGODB_DATABASE_NAME=customer_support
MONGODB_SOURCE_COLLECTION=conversation_set
MONGODB_RESULTS_COLLECTION=sentimental_analysis

# Processing Configuration
MONGODB_BATCH_SIZE=100
MONGODB_MAX_RETRIES=3
MONGODB_TIMEOUT_MS=30000
BATCH_PROCESSOR_MODE=batch

# LLM Configuration (inherited from existing system)
OLLAMA_MODEL=llama3
OLLAMA_ENDPOINT=http://localhost:11434
```

---

### 7. Monitoring & Progress Reporting System

#### Multi-Level Monitoring Architecture
```python
class ComprehensiveProgressReporter:
    """Hybrid monitoring system with configurable components"""
    
    def __init__(self, mode="production"):
        self.reporters = []
        
        if mode == "development":
            self.reporters.append(ConsoleProgressReporter())
        elif mode == "production":
            self.reporters.append(StructuredProgressLogger())
            self.reporters.append(ProgressFileReporter())
        elif mode == "interactive":
            self.reporters.append(ConsoleProgressReporter())
            self.reporters.append(StructuredProgressLogger())
```

#### Console Progress Output
```
|████████████████████████--------| 60.0% (600/1000) 
Success: 580 Failed: 20 Rate: 2.5/sec ETA: 0:02:40
```

#### Structured Log Format
```
2025-09-24 10:30:00,123 - INFO - batch_processor - Starting batch processing of 1000 conversations
2025-09-24 10:30:45,456 - INFO - batch_processor - Processed conversation 1 successfully in 45123ms
2025-09-24 10:31:30,789 - ERROR - batch_processor - Failed to process conversation 2: LLM timeout
```

#### Progress File Schema
```json
{
  "job_id": "batch_20250924_103000",
  "status": "running",
  "start_time": "2025-09-24T10:30:00",
  "total_conversations": 1000,
  "processed": 100,
  "successful": 95,
  "failed": 5,
  "current_rate": 2.5,
  "estimated_completion": "2025-09-24T17:00:00",
  "percentage_complete": 10.0
}
```

---

### 8. Database Indexing Strategy

#### Source Collection Indexes
```javascript
// Efficient filtering of unprocessed conversations
db.conversations.createIndex({ "status": 1 })

// Fast lookup by conversation number
db.conversations.createIndex({ "conversation_number": 1 }, { unique: true })

// Processing time-based queries
db.conversations.createIndex({ "last_processed_at": 1 })
```

#### Results Collection Indexes
```javascript
// Fast lookup by conversation number
db.classified_conversations.createIndex({ "conversation_number": 1 })

// Reference to source document
db.classified_conversations.createIndex({ "source_conversation_id": 1 })

// Processing job tracking
db.classified_conversations.createIndex({ "processing_metadata.batch_job_id": 1 })

// Time-based analysis
db.classified_conversations.createIndex({ "processing_metadata.processed_at": 1 })

// Classification queries
db.classified_conversations.createIndex({ "classification.intent": 1 })
db.classified_conversations.createIndex({ "classification.topic": 1 })
db.classified_conversations.createIndex({ "classification.sentiment": 1 })
```

---

### 9. Deployment Architecture

#### File Structure (Flat Organization)
```
project_root/
├── main.py                    # Existing API server (unchanged)
├── api.py                     # Existing API logic (unchanged)
├── batch_processor.py         # New: Standalone batch processor
├── mongo_client.py           # New: MongoDB operations
├── aggregator.py             # Existing (used by both)
├── prompt_builder.py         # Existing (used by both)  
├── llm_wrapper.py            # Existing (used by both)
├── classifier.py             # Existing (used by both)
├── logger.py                 # Existing (enhanced for batch)
├── error_handler.py          # Existing (enhanced for batch)
└── requirements.txt          # Updated with motor, asyncio dependencies
```

#### Docker Considerations
```dockerfile
# Additional dependencies for MongoDB batch processing
RUN pip install motor pymongo asyncio

# Environment variables for MongoDB
ENV MONGODB_CONNECTION_STRING="mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT"
ENV MONGODB_DATABASE_NAME="customer_support"
ENV MONGODB_SOURCE_COLLECTION="conversation_set"
ENV MONGODB_RESULTS_COLLECTION="sentimental_analysis"
```

---

### 10. Future Enhancements

#### Phase 3 Considerations
- **Real-time Monitoring Dashboard**: Web interface for batch job monitoring
- **Advanced Scheduling**: Cron-like scheduling with job dependencies
- **Distributed Processing**: Multi-node processing for massive datasets
- **Data Streaming**: Real-time processing of new conversations
- **Analytics Integration**: Direct integration with BI tools and dashboards
- **Auto-scaling**: Dynamic concurrency adjustment based on system load

#### Performance Optimization Opportunities
- **Connection Pooling Tuning**: Optimize MongoDB connection pool sizes
- **Batch Size Optimization**: Dynamic batch sizing based on processing performance
- **LLM Caching**: Cache similar conversation patterns to reduce processing time
- **Parallel Database Operations**: Concurrent read/write operations with proper synchronization

*End of Design Document*

---

*This implementation review confirms that the codebase fully realizes the design intent, with robust modularity, error handling, and test coverage. All major features, edge cases, and recovery strategies described in the design are present in the code. For future updates, ensure this section is kept in sync with ongoing code changes.*
