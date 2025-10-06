import asyncio
import time
import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from async_llm_wrapper import safe_ollama_classify_async
from prompt_builder import build_prompt

async def test_llm_response_time():
    # Complex multi-turn conversation with technical details
    test_conversation = """
    Customer: I'm having serious issues with your cloud storage service. Files aren't syncing and I'm getting error code E-5523
    Agent: I apologize for the sync issues. Could you tell me when this started and which devices are affected?
    Customer: It started after yesterday's system upgrade. My laptop shows "pending sync" but never completes, mobile app crashes on upload
    Agent: Thank you for those details. Are you getting any specific error messages on the mobile app?
    Customer: Yes, it says "Failed to establish secure connection" and sometimes "Authentication token expired". I've lost 3 hours of work because of this!
    Agent: I understand this is causing significant disruption. Let me check the backend systems for any known issues.
    Customer: This is the third time this month I've had problems. If this isn't fixed today, I'm canceling my subscription and moving to a competitor.
    """
    
    # Build the prompt
    prompt_result = build_prompt(1, test_conversation)
    if "error" in prompt_result:
        print(f"Error building prompt: {prompt_result['error']}")
        return
        
    # Test response time
    start_time = time.time()
    result = await safe_ollama_classify_async(prompt_result["messages"])
    end_time = time.time()
    
    # Print results
    print(f"Response time: {end_time - start_time:.2f} seconds")
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_llm_response_time())