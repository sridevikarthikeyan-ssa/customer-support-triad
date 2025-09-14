"""
test_api.py
Tests for the API layer.
"""

import pytest
from api import classify_conversation

def test_valid_request():
    import os
    os.environ["OLLAMA_MODEL"] = "llama3"
    request_json = {
        "conversation_number": "123",
        "messages": [
            {"sender": "customer", "text": "Where is my order?"},
            {"sender": "agent", "text": "Let me check for you."}
        ]
    }
    response = classify_conversation(request_json)
    assert response["conversation_number"] == "123"
    assert "classification" in response

def test_invalid_not_dict():
    response = classify_conversation([1,2,3])
    assert response["error"] == "Invalid input: not a JSON object"

def test_missing_fields():
    response = classify_conversation({"messages": []})
    assert response["error"] == "Missing required fields: conversation_number or messages"

def test_empty_messages():
    response = classify_conversation({"conversation_number": "123", "messages": []})
    assert response["error"] == "Messages must be a non-empty list"

def test_message_wrong_type():
    request_json = {
        "conversation_number": "123",
        "messages": ["not a dict"]
    }
    response = classify_conversation(request_json)
    assert response["error"] == "Each message must be a dict with sender and text fields"

def test_message_missing_fields():
    request_json = {
        "conversation_number": "123",
        "messages": [{"sender": "customer"}]
    }
    response = classify_conversation(request_json)
    assert response["error"] == "Each message must be a dict with sender and text fields"
