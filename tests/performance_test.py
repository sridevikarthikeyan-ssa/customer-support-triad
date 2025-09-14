"""
performance_test.py
Simulates 10 API requests per second to test throughput and latency.
Mocks LLM response for realism and speed.
"""

import threading
import time
from api import classify_conversation

# Sample valid input
valid_request = {
    "conversation_number": "2001",
    "messages": [
        {"sender": "customer", "text": "Where is my order?"},
        {"sender": "agent", "text": "Let me check for you."}
    ]
}

mock_llm_response = '{"classification": {"intent": "Query", "topic": "Shipping/Delivery", "sentiment": "Neutral"}}'
results = []

def run_single_request():
    start = time.time()
    response = classify_conversation(valid_request)
    end = time.time()
    results.append(end - start)
    assert "classification" in response

if __name__ == "__main__":
    # Patch LLM globally for all threads
    import llm_wrapper
    llm_wrapper.ollama_classify = lambda prompt: mock_llm_response

    threads = []
    start_time = time.time()
    # Launch 10 threads nearly simultaneously
    for _ in range(10):
        t = threading.Thread(target=run_single_request)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    end_time = time.time()
    print(f"Total time for 10 requests: {end_time - start_time:.3f} seconds")
    print(f"Average response time: {sum(results)/len(results):.3f} seconds")
    print(f"Min response time: {min(results):.3f} seconds")
    print(f"Max response time: {max(results):.3f} seconds")
