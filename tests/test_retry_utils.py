"""
Unit tests for the retry utilities module.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import time

from utils.retry_utils import (
    RetryError,
    classify_error,
    retry_with_backoff,
    async_retry
)

class TestClassifyError:
    """Tests for the classify_error function."""
    
    def test_transient_errors(self):
        """Test classification of transient errors."""
        transient_errors = [
            Exception("Connection timed out"),
            Exception("Network error occurred"),
            Exception("Connection refused"),
            Exception("Service unavailable"),
            Exception("Some random error") # Default case
        ]
        
        for error in transient_errors:
            assert classify_error(error) == "transient"
    
    def test_resource_errors(self):
        """Test classification of resource errors."""
        resource_errors = [
            Exception("Rate limit exceeded"),
            Exception("Too many requests"),
            Exception("Quota exceeded"),
            Exception("Service capacity reached"),
            Exception("Server is overloaded")
        ]
        
        for error in resource_errors:
            assert classify_error(error) == "resource"
    
    def test_permanent_errors(self):
        """Test classification of permanent errors."""
        permanent_errors = [
            # Authentication/authorization errors
            Exception("Authentication failed"),
            Exception("Unauthorized access"),
            Exception("Forbidden operation"),
            Exception("Invalid authentication token"),
            Exception("Permission denied"),
            
            # Invalid request errors
            Exception("Bad request format"),
            Exception("Invalid parameter"),
            Exception("Resource not found"),
            Exception("Syntax error in query")
        ]
        
        for error in permanent_errors:
            assert classify_error(error) == "permanent"

class TestRetryWithBackoff:
    """Tests for the retry_with_backoff function."""
    
    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self):
        """Test successful execution without retries."""
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_with_backoff(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        """Test retry logic with eventual success."""
        mock_func = AsyncMock(side_effect=[
            Exception("Connection error"),
            Exception("Timeout error"),
            "success"
        ])
        
        with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
            result = await retry_with_backoff(
                mock_func, 
                max_retries=3, 
                base_delay=1.0
            )
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep called twice for the two retries
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test retry logic when max retries are exceeded."""
        error = Exception("Persistent error")
        mock_func = AsyncMock(side_effect=[error, error, error, error])
        
        with patch("asyncio.sleep", AsyncMock()):
            with pytest.raises(RetryError) as exc_info:
                await retry_with_backoff(
                    mock_func, 
                    max_retries=3, 
                    base_delay=1.0
                )
        
        assert mock_func.call_count == 4  # Initial call + 3 retries
        assert exc_info.value.last_exception == error
    
    @pytest.mark.asyncio
    async def test_permanent_error_no_retry(self):
        """Test that permanent errors are not retried."""
        error = Exception("Authentication failed")
        mock_func = AsyncMock(side_effect=error)
        
        with pytest.raises(Exception) as exc_info:
            await retry_with_backoff(
                mock_func, 
                max_retries=3, 
                error_types=["transient", "resource"]
            )
        
        # Permanent errors should not be retried, so the function should only be called once
        assert mock_func.call_count == 1
        assert exc_info.value == error
    
    @pytest.mark.asyncio
    async def test_backoff_timing(self):
        """Test that backoff timing is correct."""
        mock_func = AsyncMock(side_effect=[
            Exception("Transient error"),
            Exception("Transient error"),
            "success"
        ])
        
        # Create a list to track sleep times
        sleep_times = []
        
        async def mock_sleep(seconds):
            sleep_times.append(seconds)
        
        with patch("asyncio.sleep", mock_sleep):
            await retry_with_backoff(
                mock_func, 
                max_retries=3,
                base_delay=1.0,
                max_delay=10.0,
                jitter=0  # Disable jitter for deterministic testing
            )
        
        # Check that backoff increases exponentially
        # First retry should sleep for 1s, second for 2s
        assert len(sleep_times) == 2
        assert sleep_times[0] == 1.0
        assert sleep_times[1] == 2.0
    
    @pytest.mark.asyncio
    async def test_max_delay_respected(self):
        """Test that max delay is respected."""
        mock_func = AsyncMock(side_effect=[
            Exception("Transient error"),
            Exception("Transient error"),
            Exception("Transient error"),
            Exception("Transient error"),
            "success"
        ])
        
        # Create a list to track sleep times
        sleep_times = []
        
        async def mock_sleep(seconds):
            sleep_times.append(seconds)
        
        with patch("asyncio.sleep", mock_sleep):
            await retry_with_backoff(
                mock_func, 
                max_retries=5,
                base_delay=2.0,
                max_delay=5.0,  # Cap at 5 seconds
                jitter=0  # Disable jitter for deterministic testing
            )
        
        # Check that delay is capped at max_delay
        assert len(sleep_times) == 4
        assert sleep_times[0] == 2.0  # 2 * (2^0)
        assert sleep_times[1] == 4.0  # 2 * (2^1)
        assert sleep_times[2] == 5.0  # Would be 8, but capped at 5
        assert sleep_times[3] == 5.0  # Would be 16, but capped at 5

class TestAsyncRetryDecorator:
    """Tests for the async_retry decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_functionality(self):
        """Test that the decorator applies retry logic."""
        
        mock_impl = AsyncMock(side_effect=[
            Exception("Transient error"),
            "success"
        ])
        
        @async_retry(max_retries=2, base_delay=1.0)
        async def test_function(*args, **kwargs):
            return await mock_impl(*args, **kwargs)
        
        with patch("asyncio.sleep", AsyncMock()):
            result = await test_function("arg1", kwarg1="value1")
        
        assert result == "success"
        assert mock_impl.call_count == 2
        mock_impl.assert_called_with("arg1", kwarg1="value1")
    
    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test that the decorator preserves function metadata."""
        
        @async_retry()
        async def test_function():
            """Test function docstring."""
            pass
        
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring."
    
    @pytest.mark.asyncio
    async def test_decorator_raises_retry_error(self):
        """Test that the decorator raises RetryError after exhausting retries."""
        error = Exception("Persistent error")
        
        @async_retry(max_retries=2, base_delay=1.0)
        async def failing_function():
            raise error
        
        with patch("asyncio.sleep", AsyncMock()):
            with pytest.raises(RetryError) as exc_info:
                await failing_function()
        
        assert "Failed after 2 retry attempts" in str(exc_info.value)
        assert exc_info.value.last_exception == error