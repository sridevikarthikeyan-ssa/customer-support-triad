
import json
import os
print(f"[DEBUG] Loaded prompt_builder.py from: {os.path.abspath(__file__)}")

# Allowed values for schema fields
INTENT_OPTIONS = [
    "Order Status", "Cancel Order", "Return/Refund", "Product Inquiry", "Technical Support", "Complaint", "Feedback", "Account/Billing", "Shipping", "Shipping/Delivery", "Other"
]
TOPIC_OPTIONS = [
    "Orders", "Payments", "Shipping/Delivery", "Shipping", "Returns", "Refunds", "Warranty", "Product Info", "Account", "Technical", "General"
]
SENTIMENT_OPTIONS = ["Positive", "Neutral", "Negative"]

# Multi-turn few-shot examples (list of messages per example)
FEW_SHOTS = [
    {
        "messages": [
            {"sender": "customer", "text": "Where is my order?"},
            {"sender": "agent", "text": "Let me check for you."}
        ],
        "output": {
            "categorization": "Requesting shipping status",
            "intent": "Order Status",
            "topic": "Shipping/Delivery",
            "sentiment": "Neutral"
        }
    },
    {
        "messages": [
            {"sender": "customer", "text": "I received a damaged product."},
            {"sender": "agent", "text": "I'm sorry to hear that. Would you like a replacement or refund?"}
        ],
        "output": {
            "categorization": "Product received damaged",
            "intent": "Return/Refund",
            "topic": "Returns",
            "sentiment": "Negative"
        }
    }
]

def build_prompt(conversation_number, aggregated_text):
    """
    Constructs the prompt for LLM classification.
    Includes strict instructions and 4 few-shot examples.
    Returns a dict with 'messages' or 'error'.
    """
    try:
        if not conversation_number or not aggregated_text:
            return {"error": "Invalid input: conversation_number and aggregated_text are required"}
        SYSTEM_PROMPT = (
            'You are a customer-support classifier. Return EXACTLY this JSON structure:\n'
            '{\n'
            '  "categorization": "brief text description",\n'
            '  "intent": "one of the allowed intents",\n'
            '  "topic": "one of the allowed topics",\n'
            '  "sentiment": "Positive/Neutral/Negative"\n'
            '}\n\n'
            'CRITICAL: Use DOUBLE QUOTES for ALL strings. Example:\n'
            '{"categorization": "Order delay issue", "intent": "Order Status", "topic": "Shipping", "sentiment": "Negative"}\n\n'
            'Allowed intents: "Order Status", "Cancel Order", "Return/Refund", "Product Inquiry",\n'
            '"Technical Support", "Complaint", "Feedback", "Account/Billing", "Shipping", "Other"\n\n'
            'Allowed topics: "Orders", "Payments", "Shipping/Delivery", "Returns", "Refunds",\n'
            '"Warranty", "Product Info", "Account", "Technical", "General"'
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        # Add few-shot examples as multi-turn user/assistant pairs
        for ex in FEW_SHOTS:
            # Combine all customer/agent messages into a single string for the user turn
            user_msgs = []
            for msg in ex["messages"]:
                if msg["sender"] == "customer":
                    user_msgs.append(f"Customer: {msg['text']}")
                elif msg["sender"] == "agent":
                    user_msgs.append(f"Agent: {msg['text']}")
            user_content = "\n".join(user_msgs)
            messages.append({"role": "user", "content": user_content})
            messages.append({"role": "assistant", "content": json.dumps(ex["output"], ensure_ascii=False)})
        # Add actual conversation
        user_query = f"Customer Query:\n{aggregated_text}\nReturn ONLY JSON:"
        messages.append({"role": "user", "content": user_query})
        return {"messages": messages}
    except Exception as e:
        return {"error": f"Prompt construction error: {str(e)}"}
