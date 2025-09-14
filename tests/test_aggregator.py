"""
test_aggregator.py
Tests for the conversation aggregator.
"""

import pytest
from aggregator import aggregate_conversation

def test_valid_aggregation():
    request_json = {
        "conversation_number": "456",
        "messages": [
            {"sender": "customer", "text": "Hello"},
            {"sender": "agent", "text": "Hi, how can I help you?"}
        ]
    }
    result = aggregate_conversation(request_json)
    assert result["conversation_number"] == "456"
    assert "aggregated_text" in result
    assert result["aggregated_text"] == "Hello Hi, how can I help you?"

def test_empty_messages():
    request_json = {"conversation_number": "456", "messages": []}
    result = aggregate_conversation(request_json)
    assert result["error"] == "Messages must be a non-empty list"

def test_message_not_dict():
    request_json = {"conversation_number": "456", "messages": ["not a dict"]}
    result = aggregate_conversation(request_json)
    assert "not a dict" in result["error"]

def test_missing_text_in_message():
    request_json = {
        "conversation_number": "456",
        "messages": [{"sender": "customer"}]
    }
    result = aggregate_conversation(request_json)
    assert "Missing text" in result["error"]

def test_multiple_missing_texts():
    request_json = {
        "conversation_number": "456",
        "messages": [
            {"sender": "customer", "text": "Hello"},
            {"sender": "agent"}
        ]
    }
    result = aggregate_conversation(request_json)
    assert "Missing text" in result["error"]
