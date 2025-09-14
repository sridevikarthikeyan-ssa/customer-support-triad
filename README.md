
# Customer Support Query Classification API

## Project Overview

This project provides an API for classifying customer support queries using Large Language Models (LLMs). It helps support teams automatically categorize and route incoming queries for faster, more accurate responses. Built with FastAPI, Uvicorn, and Ollama LLM, and containerized with Docker for easy deployment.

## Features

- Multi-turn query classification
- Strict JSON schema validation for LLM responses
- Robust error handling and logging
- Configurable LLM model and endpoint
- RESTful API endpoints for integration
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
