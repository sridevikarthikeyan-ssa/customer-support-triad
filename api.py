"""
api.py
API layer for the Customer Support Query Classification module.
"""

def classify_conversation(request_json):
    """
    Main API entry point for classifying customer support conversations.
    Accepts a JSON object, validates input, logs request, and returns classification or error response.
    """
    from logger import logger
    from error_handler import error_response
    from aggregator import aggregate_conversation
    from prompt_builder import build_prompt
    from llm_wrapper import ollama_classify
    from classifier import parse_classification
    import copy
    logger.info(f"Received request: {request_json}")
    # Validate input schema
    if not isinstance(request_json, dict):
        logger.error("Invalid input: not a JSON object")
        return error_response("Invalid input: not a JSON object")
    if "conversation_number" not in request_json:
        logger.error("Missing required field: conversation_number")
        return error_response("Missing required field: conversation_number")
    if "messages" in request_json and request_json["messages"] is not None:
        if not isinstance(request_json["messages"], list) or len(request_json["messages"]) == 0:
            logger.error("Messages must be a non-empty list")
            return error_response("Messages must be a non-empty list")
        for msg in request_json["messages"]:
            if not isinstance(msg, dict) or "sender" not in msg or "text" not in msg:
                logger.error("Each message must be a dict with sender and text fields")
                return error_response("Each message must be a dict with sender and text fields")
    elif "tweets" in request_json and request_json["tweets"] is not None:
        if not isinstance(request_json["tweets"], list) or len(request_json["tweets"]) == 0:
            logger.error("Tweets must be a non-empty list")
            return error_response("Tweets must be a non-empty list")
        for tweet in request_json["tweets"]:
            if not isinstance(tweet, dict) or "role" not in tweet or "text" not in tweet:
                logger.error("Each tweet must be a dict with role and text fields")
                return error_response("Each tweet must be a dict with role and text fields")
    else:
        logger.error("Missing required fields: messages or tweets")
        return error_response("Missing required fields: messages or tweets")

    # Aggregate conversation (handles both formats)
    agg_result = aggregate_conversation(request_json)
    if "error" in agg_result:
        return agg_result
    aggregated_text = agg_result.get("aggregated_text")

    # Build message list for LLM
    prompt_result = build_prompt(request_json["conversation_number"], aggregated_text)
    if "error" in prompt_result:
        return prompt_result
    messages = prompt_result.get("messages")
    if not messages or not isinstance(messages, list):
        logger.error("Prompt builder did not return a valid message list")
        return error_response("Prompt builder did not return a valid message list")

    # Call Ollama LLM with message list
    llm_response = ollama_classify(messages)
    if isinstance(llm_response, dict) and "error" in llm_response:
        return llm_response

    # Parse classification
    classification = parse_classification(llm_response)
    if isinstance(classification, dict) and "error" in classification:
        return classification

    # Build final response: retain all original fields, add classification
    response = copy.deepcopy(request_json)
    response["classification"] = classification
    logger.info(f"Response: {response}")
    return response
