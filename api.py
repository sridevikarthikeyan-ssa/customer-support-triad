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
    logger.info(f"Received request: {request_json}")
    # Validate input schema
    if not isinstance(request_json, dict):
        logger.error("Invalid input: not a JSON object")
        return error_response("Invalid input: not a JSON object")
    if "conversation_number" not in request_json or "messages" not in request_json:
        logger.error("Missing required fields: conversation_number or messages")
        return error_response("Missing required fields: conversation_number or messages")
    if not isinstance(request_json["messages"], list) or len(request_json["messages"]) == 0:
        logger.error("Messages must be a non-empty list")
        return error_response("Messages must be a non-empty list")
    for msg in request_json["messages"]:
        if not isinstance(msg, dict) or "sender" not in msg or "text" not in msg:
            logger.error("Each message must be a dict with sender and text fields")
            return error_response("Each message must be a dict with sender and text fields")
    # Aggregate conversation
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
    # Build final response
    response = {
        "conversation_number": request_json["conversation_number"],
        "messages": request_json["messages"],
        "classification": classification
    }
    logger.info(f"Response: {response}")
    return response
