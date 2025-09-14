"""
test_llm_wrapper.py
Tests for the LLM wrapper.
"""

import pytest
import os
import json
from llm_wrapper import ollama_classify

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)  # Add .text attribute for compatibility
    def json(self):
        return self._json
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception("HTTP error")

def test_valid_llm_call(monkeypatch):
    def mock_post(url, json, timeout):
        return MockResponse({"response": "Classification result"})
    monkeypatch.setattr("requests.post", mock_post)
    os.environ["OLLAMA_MODEL"] = "llama3"
    result = ollama_classify("Test prompt")
    assert result == "Classification result"

def test_missing_model_env(monkeypatch):
    def mock_post(url, json, timeout):
        return MockResponse({"response": "Should not be called"})
    monkeypatch.setattr("requests.post", mock_post)
    if "OLLAMA_MODEL" in os.environ:
        del os.environ["OLLAMA_MODEL"]
    result = ollama_classify("Test prompt")
    assert result["error"] == "OLLAMA_MODEL environment variable not set"

def test_llm_timeout(monkeypatch):
    def mock_post(url, json, timeout):
        raise Exception("Timeout")
    monkeypatch.setattr("requests.post", mock_post)
    os.environ["OLLAMA_MODEL"] = "llama3"
    result = ollama_classify("Test prompt")
    assert "error" in result
