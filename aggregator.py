"""
aggregator.py
Aggregates all messages in a customer conversation.
"""

def map_role(role):
    if not role:
        return "unknown"
    role_lc = role.strip().lower()
    if role_lc in ("service provider", "agent"):
        return "agent"
    if role_lc in ("customer", "user"):
        return "customer"
    return "unknown"

def tweets_to_messages(tweets):
    return [
        {
            "sender": map_role(tweet.get("role")),
            "text": tweet.get("text", "")
        }
        for tweet in tweets
    ]

def aggregate_conversation(request_json):
    """
    Aggregates all messages in a customer conversation.
    Supports both production-grade 'tweets' and legacy 'messages' formats.
    Returns aggregated text or error response if input is invalid.
    """
    from logger import logger
    from error_handler import error_response
    try:
        if "tweets" in request_json:
            messages = tweets_to_messages(request_json["tweets"])
        else:
            messages = request_json.get("messages", [])
        if not isinstance(messages, list) or len(messages) == 0:
            logger.error("Messages must be a non-empty list")
            return error_response("Messages must be a non-empty list")
        aggregated_texts = []
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                logger.error(f"Message at index {idx} is not a dict")
                return error_response(f"Message at index {idx} is not a dict")
            text = msg.get("text", "")
            # Skip empty text, do not error
            if text:
                aggregated_texts.append(text)
        if len(aggregated_texts) == 0:
            logger.error("All messages/tweets have empty text")
            return error_response("All messages/tweets have empty text")
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
