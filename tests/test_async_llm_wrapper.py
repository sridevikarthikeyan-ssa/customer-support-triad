"""
test_async_llm_wrapper.py
Tests for the asynchronous LLM wrapper component.
"""
import os
import json
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Import the module to test
import sys
sys.path.append("..")
import async_llm_wrapper


@pytest.mark.asyncio
async def test_ollama_classify_async_success():
    """Test successful LLM interaction with proper JSON response."""
    # Create proper async mocks
    response_data = {
        "message": {"content": '{"intent": "Inquiry", "topic": "Service", "sentiment": "Neutral"}'}
    }
    
    # Create a mock response with status code and json method
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=response_data)
    
    # Create a mock session
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.closed = False
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "llama3"}):
            messages = [{"role": "user", "content": "test message"}]
            result = await async_llm_wrapper.ollama_classify_async(messages)
            
            # Check that the result is parsed correctly
            assert result == {"intent": "Inquiry", "topic": "Service", "sentiment": "Neutral"}


@pytest.mark.asyncio
async def test_ollama_classify_async_json_extraction():
    """Test successful extraction of JSON from text that includes non-JSON content."""
    response_data = {
        "message": {"content": 'Here is the classification:\n{"intent": "Complaint", "topic": "Billing", "sentiment": "Negative"}\nI hope this helps!'}
    }
    
    # Create a mock response with status code and json method
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=response_data)
    
    # Create a mock session
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.closed = False
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "llama3"}):
            result = await async_llm_wrapper.ollama_classify_async([{"role": "user", "content": "test message"}])
            
            # Check that the JSON was extracted correctly from the text
            assert result == {"intent": "Complaint", "topic": "Billing", "sentiment": "Negative"}


@pytest.mark.asyncio
async def test_ollama_classify_async_request_error():
    """Test handling of HTTP request errors."""
    mock_session = AsyncMock()
    mock_session.post.side_effect = Exception("Connection error")
    mock_session.closed = False
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "llama3"}):
            result = await async_llm_wrapper.ollama_classify_async([{"role": "user", "content": "test message"}])
            
            # Check that the error was handled properly
            assert "error" in result
            assert "Connection error" in result["error"]


@pytest.mark.asyncio
async def test_ollama_classify_async_missing_model():
    """Test handling of missing OLLAMA_MODEL environment variable."""
    with patch.dict(os.environ, {}, clear=True):  # Clear environment variables
        result = await async_llm_wrapper.ollama_classify_async([{"role": "user", "content": "test message"}])
        
        # Check that the error was handled properly
        assert "error" in result
        assert "OLLAMA_MODEL environment variable not set" in result["error"]


@pytest.mark.asyncio
async def test_safe_ollama_classify_async_with_retry():
    """Test the retry logic for transient failures."""
    # Create a success response for the retry test
    success_response = {"intent": "Inquiry", "topic": "Service", "sentiment": "Neutral"}
    
    # Create a mock that fails twice then succeeds
    mock_ollama = AsyncMock()
    mock_ollama.side_effect = [
        Exception("Temporary connection error"),
        Exception("Still failing"),
        success_response
    ]
    
    # Test the safe_ollama_classify_async function which has retry logic
    with patch.object(async_llm_wrapper, "ollama_classify_async", mock_ollama):
        with patch.object(async_llm_wrapper, "RETRY_DELAYS", [0.01, 0.01, 0.01]):
            result = await async_llm_wrapper.safe_ollama_classify_async([{"role": "user", "content": "test message"}])
            
            # Check that the result was eventually successful after retries
            assert result == success_response
            
            # Verify original function was called 3 times (initial + 2 retries before success)
            assert mock_ollama.call_count == 3


@pytest.mark.asyncio
async def test_ollama_classify_async_parsing_error():
    """Test handling of JSON parsing errors."""
    # Create a response with invalid JSON
    response_data = {
        "message": {"content": 'This is not valid JSON content'}
    }
    
    # Create a mock response with status code and json method
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=response_data)
    
    # Create a mock session
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.closed = False
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "llama3"}):
            result = await async_llm_wrapper.ollama_classify_async([{"role": "user", "content": "test message"}])
            
            # Check that the error was handled properly
            assert "error" in result


@pytest.mark.asyncio
async def test_safe_ollama_classify_async_max_retries():
    """Test that the safe wrapper doesn't retry indefinitely."""
    # Create a mock that always fails
    mock_ollama = AsyncMock()
    mock_ollama.side_effect = Exception("Persistent error")
    
    with patch.object(async_llm_wrapper, "ollama_classify_async", mock_ollama):
        with patch.object(async_llm_wrapper, "MAX_RETRIES", 3):
            with patch.object(async_llm_wrapper, "RETRY_DELAYS", [0.01, 0.01, 0.01]):
                messages = [{"role": "user", "content": "test message"}]
                result = await async_llm_wrapper.safe_ollama_classify_async(messages)
                
                # Check that we got an error response after exhausting retries
                assert "error" in result
                
                # Verify the function was called exactly MAX_RETRIES + 1 times (original + retries)
                assert mock_ollama.call_count == 4


@pytest.mark.asyncio
async def test_concurrent_ollama_calls():
    """Test that multiple concurrent calls can be made without issues."""
    # Create a list to track calls to the mock post function
    call_count = []
    
    # Create a successful mock response
    response_data = {
        "message": {"content": '{"result": "ok"}'}
    }
    
    # Track calls using a side effect
    async def side_effect(*args, **kwargs):
        call_count.append(1)
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=response_data)
        return mock_response
    
    # Create a mock session
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(side_effect=side_effect)
    mock_session.closed = False
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "llama3"}):
            # Make multiple concurrent calls
            messages = [{"role": "user", "content": "test message"}]
            tasks = [
                async_llm_wrapper.ollama_classify_async(messages) for _ in range(5)
            ]
            results = await asyncio.gather(*tasks)
            
            # Check that all calls succeeded with the expected response
            for result in results:
                assert result == {"result": "ok"}
            
            # Verify we made 5 calls
            assert len(call_count) == 5