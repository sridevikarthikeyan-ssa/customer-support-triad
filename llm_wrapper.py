"""
llm_wrapper.py
Handles LLM connectivity and interaction.
"""


def ollama_classify(messages):
    """
    Sends message list to Ollama LLM (localhost) and returns parsed JSON response.
    Uses OLLAMA_MODEL environment variable for model selection.
    Handles errors and logs interactions.
    """
    import os
    import requests
    import json
    from logger import logger
    from error_handler import error_response
    try:
        ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL")
        if not ollama_model:
            logger.error("OLLAMA_MODEL environment variable not set")
            return {"error": "OLLAMA_MODEL environment variable not set"}
        url = f"{ollama_endpoint}/api/chat"
        payload = {
            "model": ollama_model,
            "messages": messages,
            "options": {"num_predict": 700},
            "stream": False
        }
        logger.info(f"Sending messages to Ollama: {payload}")
        response = requests.post(url, json=payload, timeout=None)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Raw LLM response: {data}")
        content = ""
        if "message" in data:
            content = data["message"].get("content", "").strip()
        elif "messages" in data and len(data["messages"]) > 0:
            content = data["messages"][0].get("content", "").strip()
        if not content:
            logger.error("Empty LLM response content")
            return error_response("Empty LLM response content")
        try:
            parsed = json.loads(content)
            logger.info(f"Extracted JSON object: {parsed}")
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse LLM response content as JSON: {e}")
            # Try to extract JSON substring
            start, end = content.find("{"), content.rfind("}")
            if start != -1 and end != -1:
                try:
                    parsed = json.loads(content[start:end+1])
                    logger.info(f"Extracted JSON substring: {parsed}")
                    return parsed
                except Exception as e2:
                    logger.error(f"Failed to parse JSON substring: {e2}")
            return error_response("Failed to parse LLM response as JSON")
    except requests.exceptions.Timeout:
        logger.error("LLM request timed out")
        return {"error": "LLM request timed out"}
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM connectivity error: {str(e)}")
        return {"error": "LLM connectivity error"}
    except Exception as e:
        logger.error(f"LLM error: {str(e)}")
        return {"error": "LLM error"}
