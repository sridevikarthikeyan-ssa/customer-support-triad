"""
classifier.py
Parses and validates LLM output for classification.
"""

def parse_classification(response):
    """
    Parses LLM output and validates classification schema (intent, topic, sentiment).
    Returns parsed result or error response.
    """
    import json
    from logger import logger
    from error_handler import error_response
    try:
        if not response:
            logger.error("Empty LLM response")
            return error_response("Empty LLM response")
        # Parse response (assume JSON string)
        if isinstance(response, str):
            classification = json.loads(response)
        elif isinstance(response, dict):
            classification = response
        else:
            logger.error("Invalid response type")
            return error_response("Invalid response type")
        # Validate schema
        required_fields = ["intent", "topic", "sentiment"]
        if "classification" in classification:
            class_obj = classification["classification"]
        else:
            class_obj = classification
        for field in required_fields:
            if field not in class_obj:
                logger.error(f"Missing field in classification: {field}")
                return error_response(f"Missing field in classification: {field}")
        logger.info(f"Classification parsed: {class_obj}")
        return class_obj
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response as JSON")
        return error_response("Failed to parse LLM response as JSON")
    except Exception as e:
        logger.error(f"Parsing error: {str(e)}")
        return error_response("Parsing error")
