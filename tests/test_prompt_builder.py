"""
test_prompt_builder.py
Tests for the prompt builder.
"""

import pytest
from prompt_builder import build_prompt

def test_valid_prompt():
    conversation_number = "789"
    aggregated_text = "Customer: I want to cancel my subscription. Agent: I can help you with that."
    result = build_prompt(conversation_number, aggregated_text)
    assert "prompt" in result
    assert f"Conversation #{conversation_number}" in result["prompt"]
    assert "Instructions:" in result["prompt"]
    assert "Few-shot Sample:" in result["prompt"]

def test_empty_aggregated_text():
    conversation_number = "789"
    aggregated_text = ""
    result = build_prompt(conversation_number, aggregated_text)
    assert "error" in result

def test_error_handling():
    # Simulate error by passing None (should not raise exception)
    result = build_prompt(None, None)
    assert "error" in result
