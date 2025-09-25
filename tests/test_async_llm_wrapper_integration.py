"""
test_async_llm_wrapper_integration.py
Integration tests for the asynchronous LLM wrapper component.
Tests actual LLM calls to a local Ollama instance.
"""
import os
import asyncio
import time
import pytest
import json
import logging
from datetime import datetime

# Configure logging to show INFO level messages
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import the module to test
import sys
sys.path.append("..")
import async_llm_wrapper

# Set the Ollama model to use for testing
# This should be a model that's available on your local Ollama instance
TEST_MODEL = "llama3"

@pytest.mark.asyncio
@pytest.mark.timeout(600)  # 10 minute timeout for this test
async def test_concurrent_ollama_calls_real():
    """Test making multiple concurrent real calls to Ollama."""
    # Skip test if OLLAMA_MODEL environment variable isn't set
    if not os.environ.get("OLLAMA_MODEL"):
        os.environ["OLLAMA_MODEL"] = TEST_MODEL
        print(f"Setting OLLAMA_MODEL to {TEST_MODEL}")
    
    # Set up test messages - reduced to 3 for faster testing
    test_messages = [
        [{"role": "user", "content": f"Please classify this customer query in JSON format with 'intent', 'topic', and 'sentiment' fields: 'I can't access my account after the recent update. This is really frustrating!'"}],
        [{"role": "user", "content": f"Please classify this customer query in JSON format with 'intent', 'topic', and 'sentiment' fields: 'Thank you for your excellent support. My issue has been resolved.'"}],
        [{"role": "user", "content": f"Please classify this customer query in JSON format with 'intent', 'topic', and 'sentiment' fields: 'How do I reset my password? I forgot my login credentials.'"}],
    ]
    
    print(f"\nStarting {len(test_messages)} concurrent Ollama LLM calls...")
    print(f"Using Ollama model: {os.environ.get('OLLAMA_MODEL')}")
    start_time = time.time()
    
    # Make concurrent calls
    tasks = [
        async_llm_wrapper.safe_ollama_classify_async(message) for message in test_messages
    ]
    
    print(f"Tasks created, awaiting results...")
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Log results
    print(f"\nCompleted {len(test_messages)} concurrent calls in {elapsed_time:.2f} seconds")
    print(f"Average time per request: {elapsed_time/len(test_messages):.2f} seconds")
    
    for i, result in enumerate(results):
        print(f"\n=== RESULT {i+1} ===")
        print(f"PROMPT SENT TO LLM:")
        print(f"{json.dumps(test_messages[i], indent=2)}")
        print(f"\nLLM RESPONSE (PARSED):")
        print(f"{json.dumps(result, indent=2)}")
        
        # Validate result structure
        assert isinstance(result, dict)
        if "error" not in result:
            assert "intent" in result
            assert "topic" in result
            assert "sentiment" in result
    
    # Compare sequential vs. concurrent
    print("\nTesting sequential execution for comparison:")
    seq_start_time = time.time()
    
    sequential_results = []
    for i, message in enumerate(test_messages):
        print(f"  Starting sequential call {i+1}/{len(test_messages)}...")
        call_start = time.time()
        result = await async_llm_wrapper.safe_ollama_classify_async(message)
        call_elapsed = time.time() - call_start
        print(f"  Call {i+1} completed in {call_elapsed:.2f} seconds")
        sequential_results.append(result)
    
    seq_end_time = time.time()
    seq_elapsed_time = seq_end_time - seq_start_time
    
    print(f"Sequential execution completed in {seq_elapsed_time:.2f} seconds")
    print(f"Speedup from concurrency: {seq_elapsed_time / elapsed_time:.2f}x")
    
    # Make sure we got results for all calls
    assert len(results) == len(test_messages)
    

if __name__ == "__main__":
    # This allows running the test directly with python
    asyncio.run(test_concurrent_ollama_calls_real())