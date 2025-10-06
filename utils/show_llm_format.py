"""
Show an example of the prompt sent to the LLM and the expected response format.
"""
import json

# Example of what we send to the LLM
customer_query = "I can't access my account after the recent update. This is really frustrating!"

prompt = [
    {
        "role": "user",
        "content": f"Please classify this customer query in JSON format with 'intent', 'topic', and 'sentiment' fields: '{customer_query}'"
    }
]

print("\n==== EXAMPLE LLM INTERACTION ====")
print("\nWhat we send to the LLM:")
print(json.dumps(prompt, indent=2))

# Example of what we expect to get back (raw format before parsing)
expected_llm_raw_response = {
    "message": {
        "role": "assistant", 
        "content": '{\n  "intent": "Complaint",\n  "topic": "Account Access",\n  "sentiment": "Negative"\n}'
    }
}

print("\nRaw LLM response (before parsing):")
print(json.dumps(expected_llm_raw_response, indent=2))

# The content we extract and parse as JSON
content = expected_llm_raw_response["message"]["content"]
print("\nExtracted content from LLM response:")
print(content)

# The final parsed result
parsed_result = json.loads(content)
print("\nFinal parsed classification:")
print(json.dumps(parsed_result, indent=2))