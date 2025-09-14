# Customer Support Query Classification API

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
