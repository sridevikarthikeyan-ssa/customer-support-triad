# Batch Processor Fix Documentation

## Problem Summary

The batch processor was experiencing issues connecting to MongoDB and processing documents despite showing successful connection logs. Upon investigation, several mismatched method names and incorrect handling of document fields were identified.

## Changes Made

### 1. MongoDB Connection Handling

**Issue:** The original code expected a return value from `mongo_client.connect()`, but this method doesn't return anything.
**Fix:** Updated the `connect()` method to properly handle the MongoDB client's connect method behavior.

```python
# BEFORE:
connected = await self.mongo_client.connect()
if connected:
    logger.info("Successfully connected to MongoDB")
    return True
else:
    logger.error("Failed to connect to MongoDB")
    return False

# AFTER:
# The connect method doesn't return a value, it raises an exception on failure
await self.mongo_client.connect()
logger.info("Successfully connected to MongoDB")
return True
```

### 2. Method Name Mismatches

**Issue:** The batch processor was using method names that didn't exist in the MongoDB client.
**Fix:** Updated method calls to match the actual methods in the MongoDB client:

| Original Method | Corrected Method |
|-----------------|------------------|
| `get_unprocessed_documents` | `fetch_unprocessed_documents` |
| `store_classification` | `store_classification_result` |
| `mark_as_processed` | `update_document_status` |

Example:

```python
# BEFORE:
documents, more_available, last_id = await self.mongo_client.get_unprocessed_documents(
    batch_size=self.batch_size, 
    last_id=self.last_processed_id
)

# AFTER:
documents, first_id, last_id = await self.mongo_client.fetch_unprocessed_documents(
    batch_size=self.batch_size, 
    last_object_id=self.last_processed_id
)
```

### 3. Document Field Processing

**Issue:** The code was looking for a `query` field that didn't exist in the documents.
**Fix:** Updated to extract text from the `tweets` field:

```python
# BEFORE:
query = document.get("query", "")
if not query:
    logger.warning(f"Document {doc_id} has no query field")
    await self._mark_as_processed(doc_id, {"error": "No query field"})
    return result

# AFTER:
tweets = document.get("tweets", [])
if not tweets:
    logger.warning(f"Document {doc_id} has no tweets field")
    await self._mark_as_processed(doc_id, {"error": "No tweets field"})
    return result

# Extract text from tweets
conversation_text = ""
for tweet in tweets:
    if isinstance(tweet, dict) and "text" in tweet:
        conversation_text += tweet["text"] + " "

if not conversation_text.strip():
    logger.warning(f"Document {doc_id} has no text content in tweets")
    await self._mark_as_processed(doc_id, {"error": "No text content in tweets"})
    return result
```

### 4. Environment Variable Handling

**Issue:** Environment variables were hardcoded in the run script.
**Fix:** Updated to use the existing `.env` file using `dotenv`.

```python
# BEFORE:
os.environ["OLLAMA_MODEL"] = "gpt-oss"
os.environ["OLLAMA_ENDPOINT"] = "http://localhost:11434"

# AFTER:
from dotenv import load_dotenv
load_dotenv()  # Loads variables from .env file
```

## How the Batch Processor Works

The batch processor follows these steps:

1. **Initialize**: Sets up MongoDB connection and batch processing parameters.

2. **Connect to MongoDB**: Establishes connection to the database and verifies connectivity.

3. **Fetch Unprocessed Documents**: Retrieves documents from the `conversation_set` collection that haven't been processed yet, using cursor-based pagination.

4. **Process Documents**: For each document:
   - Extracts conversation text from the `tweets` field
   - Updates document status to "processing"
   - Prepares the conversation for the LLM
   - Calls the LLM for classification
   - Stores classification result in the `sentimental_analysis` collection
   - Updates document status to "processed" or "failed"

5. **Handle Errors**: Implements retry logic for failed operations and maintains checkpoints.

6. **Close Connection**: Properly closes the MongoDB connection when processing completes.

## How to Identify Which Documents Are Selected

The batch processor selects documents based on these criteria:

1. Documents in the `conversation_set` collection
2. Documents without `status = "processed"`
3. Documents are sorted by `_id`

To see which documents would be selected, you can:

1. Run `check_source_documents.py`, which shows:
   - Document IDs
   - Conversation numbers
   - Tweet counts
   - Sample of the first tweet text

2. Query MongoDB directly with a filter:

   ```javascript
   db.conversation_set.find({"status": {$ne: "processed"}}).limit(5)
   ```

3. Check the logs during batch processor execution, which will display:

   ```plaintext
   INFO: Fetched {n} unprocessed documents
   INFO: Calling LLM for document {document_id}
   ```

After processing, check the `sentimental_analysis` collection for the classification results:

```javascript
db.sentimental_analysis.find({}).sort({processed_at: -1}).limit(5)
```