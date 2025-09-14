# Design & Architecture Document

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


*End of Design Document*
