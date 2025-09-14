"""
main.py
FastAPI server for Customer Support Query Classification
"""

from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Response, status
from pydantic import BaseModel
from api import classify_conversation
import uvicorn

app = FastAPI()

class Message(BaseModel):
    sender: str
    text: str

class ConversationRequest(BaseModel):
    conversation_number: str
    messages: list[Message]

@app.post("/classify")
async def classify(request: ConversationRequest, response: Response):
    # Convert Pydantic model to dict for compatibility
    result = classify_conversation(request.dict())
    # Set status code based on error type
    if isinstance(result, dict) and "error" in result:
        err = result["error"].lower()
        if ("input" in err or "message" in err or "conversation_number" in err or "aggregated_text" in err):
            response.status_code = status.HTTP_400_BAD_REQUEST
        elif ("llm connectivity" in err or "timed out" in err):
            response.status_code = status.HTTP_502_BAD_GATEWAY
        else:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        response.status_code = status.HTTP_200_OK
    return result

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
