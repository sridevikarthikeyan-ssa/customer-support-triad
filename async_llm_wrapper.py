"""
async_llm_wrapper.py
Asynchronous LLM connectivity and interaction.

This module provides async versions of the LLM wrapper functions
for use with concurrent processing in the batch processor.
"""
import os
import json
import asyncio
import aiohttp
from logger import logger
from error_handler import error_response


# Configuration for retry logic
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # Exponential backoff: 2s, 4s, 8s


async def ollama_classify_async(messages):
    """
    Asynchronously sends message list to Ollama LLM and returns parsed JSON response.
    Uses OLLAMA_MODEL environment variable for model selection.
    Handles errors and logs interactions.
    
    Args:
        messages (list): List of message objects in the format [{"role": "...", "content": "..."}]
        
    Returns:
        dict: Parsed JSON response or error object
    """
    try:
        ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL")
        if not ollama_model:
            logger.error("OLLAMA_MODEL environment variable not set")
            return {"error": "OLLAMA_MODEL environment variable not set"}
        
        url = f"{ollama_endpoint}/api/chat"
        payload = {
            "model": ollama_model,
            "messages": messages,
            "options": {
                "num_predict": 300,  # Reduced from 700
                "temperature": 0.1,  # Add temperature for more focused responses
                "top_p": 0.9,       # Nucleus sampling
                "repeat_penalty": 1.1  # Minimize repetition
            },
            "stream": False
        }
        
        logger.info(f"Sending messages to Ollama (async): {payload}")
        
        # Use aiohttp for async HTTP requests
        session = aiohttp.ClientSession()
        try:
            async with session:
                # Increased timeout to 300 seconds (5 minutes) to accommodate slower model responses
                response = await session.post(url, json=payload, timeout=300)
                if response.status != 200:
                    logger.error(f"LLM returned error status: {response.status}")
                    return {"error": f"LLM error status: {response.status}"}
                
                data = await response.json()
                logger.info(f"Raw LLM response (async): {data}")
                
                content = ""
                if "message" in data:
                    content = data["message"].get("content", "").strip()
                elif "messages" in data and len(data["messages"]) > 0:
                    content = data["messages"][0].get("content", "").strip()
                
                # Log the raw content from LLM for debugging
                logger.info(f"Raw LLM content (before parsing): {content}")
                
                if not content:
                    logger.error("Empty LLM response content")
                    return error_response("Empty LLM response content")
                
                try:
                    parsed = json.loads(content)
                    logger.info(f"Extracted JSON object (async): {parsed}")
                    return parsed
                except Exception as e:
                    logger.error(f"Failed to parse LLM response content as JSON: {e}")
                    # Try to extract JSON substring
                    start, end = content.find("{"), content.rfind("}")
                    if start != -1 and end != -1:
                        try:
                            parsed = json.loads(content[start:end+1])
                            logger.info(f"Extracted JSON substring (async): {parsed}")
                            return parsed
                        except Exception as e2:
                            logger.error(f"Failed to parse JSON substring: {e2}")
                    return error_response("Failed to parse LLM response as JSON")
        finally:
            if not session.closed:
                await session.close()
    
    except asyncio.TimeoutError:
        logger.error("LLM async request timed out")
        return {"error": "LLM request timed out"}
    except aiohttp.ClientError as e:
        logger.error(f"LLM connectivity error (async): {str(e)}")
        return {"error": f"LLM connectivity error: {str(e)}"}
    except Exception as e:
        logger.error(f"LLM error (async): {str(e)}")
        return {"error": f"LLM error: {str(e)}"}


async def safe_ollama_classify_async(messages, retries=None, delay_index=0):
    """
    Safely calls the ollama_classify_async function with retry logic.
    Implements exponential backoff for transient failures.
    
    Args:
        messages (list): List of message objects
        retries (int, optional): Number of retries remaining. Defaults to MAX_RETRIES.
        delay_index (int, optional): Index into RETRY_DELAYS for current retry. Defaults to 0.
        
    Returns:
        dict: LLM response or error object after retries are exhausted
    """
    if retries is None:
        retries = MAX_RETRIES
        
    try:
        return await ollama_classify_async(messages)
    except Exception as e:
        if retries > 0:
            # Get the delay for this retry attempt
            delay = RETRY_DELAYS[min(delay_index, len(RETRY_DELAYS) - 1)]
            logger.warning(f"LLM call failed, retrying in {delay}s... ({retries} attempts left)")
            
            # Wait before retrying
            await asyncio.sleep(delay)
            
            # Recursive call with decremented retries
            return await safe_ollama_classify_async(
                messages,
                retries - 1,
                delay_index + 1
            )
        else:
            logger.error(f"LLM call failed after all retries: {str(e)}")
            return {"error": f"LLM error after {MAX_RETRIES} retries: {str(e)}"}