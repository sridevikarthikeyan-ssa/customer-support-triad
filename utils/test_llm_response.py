"""
test_llm_response.py

A simple script to test the LLM response with a single query.
"""
import os
import sys
import json
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from async_llm_wrapper import ollama_classify_async

async def test_llm_response():
    """Send a test message to the LLM and display the response."""
    # Set the model
    os.environ["OLLAMA_MODEL"] = "llama3"
    
    # The query
    customer_query = "I can't access my account after the recent update. This is really frustrating!"
    
    # Create the message
    message = [{
        "role": "user", 
        "content": f"Please classify this customer query in JSON format with 'intent', 'topic', and 'sentiment' fields: '{customer_query}'"
    }]
    
    print("\n==== TEST LLM RESPONSE ====")
    print("Sending message to LLM:")
    print(json.dumps(message, indent=2))
    print("\nWaiting for response...")
    
    # Send the query to the LLM
    response = await ollama_classify_async(message)
    
    print("\nParsed response from LLM:")
    print(json.dumps(response, indent=2))

if __name__ == "__main__":
    asyncio.run(test_llm_response())