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

*End of Specification*
