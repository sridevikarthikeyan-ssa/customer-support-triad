"""
test_error_handler.py
Tests for the error handler.
"""

from error_handler import error_response

def test_error_response_format():
    msg = "Test error message"
    result = error_response(msg)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] == msg

def test_error_response_empty_message():
    result = error_response("")
    assert "error" in result
    assert result["error"] == ""
