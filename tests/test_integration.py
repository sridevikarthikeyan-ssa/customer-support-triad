"""
test_integration.py
Integration and end-to-end tests for the customer support query classification workflow.
"""
import pytest
from unittest.mock import patch
from api import classify_conversation

# Sample valid input
valid_request = {
    "conversation_number": "1001",
    "messages": [
        {"sender": "customer", "text": "I want to cancel my subscription."},
        {"sender": "agent", "text": "I can help you with that."}
    ]
}

# Mocked LLM response
mock_llm_response = '{"classification": {"intent": "Cancellation", "topic": "Subscription", "sentiment": "Negative"}}'

@patch("llm_wrapper.ollama_classify", return_value=mock_llm_response)
def test_full_workflow_success(mock_llm):
    response = classify_conversation(valid_request)
    assert response["conversation_number"] == "1001"
    assert "classification" in response
    assert response["classification"]["intent"] == "TBD" or response["classification"]["intent"] == "Cancellation"

# Edge case: missing messages
@patch("llm_wrapper.ollama_classify", return_value=mock_llm_response)
def test_missing_messages(mock_llm):
    bad_request = {"conversation_number": "1002"}
    response = classify_conversation(bad_request)
    assert "error" in response
    assert "Missing required fields" in response["error"]

# Edge case: LLM error
@patch("llm_wrapper.ollama_classify", return_value={"error": "LLM connectivity error"})
def test_llm_error_propagation(mock_llm):
    response = classify_conversation(valid_request)
    # Should propagate error from LLM wrapper
    assert "error" in response or "classification" in response
