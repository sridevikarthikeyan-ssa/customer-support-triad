"""
test_logger.py
Tests for the logger.
"""

import logging
from logger import logger

def test_logger_instance():
    assert isinstance(logger, logging.Logger)
    assert logger.name == "customer_support_query_classification"

def test_logger_info(caplog):
    with caplog.at_level(logging.INFO):
        logger.info("Test info log")
        assert "Test info log" in caplog.text
