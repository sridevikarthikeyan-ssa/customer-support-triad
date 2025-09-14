"""
test_classifier.py
Tests for the classifier.
"""

import pytest
from classifier import parse_classification

def test_valid_classification_dict():
    response = {
        "classification": {
            "intent": "Cancellation",
            "topic": "Subscription",
            "sentiment": "Negative"
        }
    }
    result = parse_classification(response)
    assert result["intent"] == "Cancellation"
    assert result["topic"] == "Subscription"
    assert result["sentiment"] == "Negative"

def test_valid_classification_json():
    response = '{"classification": {"intent": "Cancellation", "topic": "Subscription", "sentiment": "Negative"}}'
    result = parse_classification(response)
    assert result["intent"] == "Cancellation"
    assert result["topic"] == "Subscription"
    assert result["sentiment"] == "Negative"

def test_missing_field():
    response = {
        "classification": {
            "intent": "Cancellation",
            "topic": "Subscription"
        }
    }
    result = parse_classification(response)
    assert "error" in result
    assert "Missing field" in result["error"]

def test_invalid_json():
    response = '{"classification": {"intent": "Cancellation", "topic": "Subscription" "sentiment": "Negative"}}'  # Missing comma
    result = parse_classification(response)
    assert "error" in result
    assert "Failed to parse" in result["error"]

def test_empty_response():
    result = parse_classification("")
    assert "error" in result
    assert "Empty LLM response" in result["error"]
