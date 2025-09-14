"""
logger.py
Centralized logging for the module.
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("customer_support_query_classification")
