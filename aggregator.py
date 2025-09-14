"""
aggregator.py
Aggregates all messages in a customer conversation.
"""

def aggregate_conversation(request_json):
    """
    Aggregates all messages in a customer conversation.
    Returns aggregated text or error response if input is invalid.
    """
    from logger import logger
    from error_handler import error_response
    try:
        messages = request_json.get("messages", [])
        if not isinstance(messages, list) or len(messages) == 0:
            logger.error("Messages must be a non-empty list")
            return error_response("Messages must be a non-empty list")
        aggregated_texts = []
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                logger.error(f"Message at index {idx} is not a dict")
                return error_response(f"Message at index {idx} is not a dict")
            text = msg.get("text")
            if not text:
                logger.error(f"Missing text in message at index {idx}")
                return error_response(f"Missing text in message at index {idx}")
            aggregated_texts.append(text)
        aggregated_text = " ".join(aggregated_texts)
        logger.info(f"Aggregated messages: {aggregated_text}")
        return {
            "conversation_number": request_json.get("conversation_number"),
            "aggregated_text": aggregated_text,
            "messages": messages
        }
    except Exception as e:
        logger.error(f"Aggregation error: {str(e)}")
        return error_response("Aggregation error")
