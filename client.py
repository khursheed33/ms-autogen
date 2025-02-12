import json
import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from autogen import AssistantAgent, UserProxyAgent
from uuid import uuid4
from fastapi.responses import HTMLResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define AI Assistant
ai_assistant = AssistantAgent(
    "ai_assistant",
    llm_config={
        "model": "gpt-4",
        "api_key": OPENAI_API_KEY,
    }
)

# Define User Proxy with Human-in-the-Loop
user_proxy = UserProxyAgent("user_proxy", code_execution_config={"use_docker": False})

# Dictionary to store conversation history for each session
sessions = {}
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket chat endpoint with session management"""
    await websocket.accept()
    session_id = str(uuid4())  # Generate a unique session ID
    sessions[session_id] = {"conversation": [], "needs_human": False}  # Initialize as a dictionary
    logging.info(f"New WebSocket session created: {session_id}")

    try:
        while True:
            data = await websocket.receive_text()
            logging.info(f"Received message from session {session_id}: {data}")

            # Parse the incoming message (assuming it's JSON)
            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
            except json.JSONDecodeError:
                user_message = data  # Fallback to plain text if JSON parsing fails

            # Get AI response and human intervention status
            response, needs_human = await chat_with_human_in_loop(session_id, user_message)

            # Send JSON response
            response_data = {
                "response": response,
                "human_intervention": needs_human
            }
            await websocket.send_text(json.dumps(response_data))

            logging.info(f"Sent response to session {session_id}: {response_data}")
    except WebSocketDisconnect:
        logging.info(f"WebSocket connection closed for session: {session_id}")
        del sessions[session_id]

async def chat_with_human_in_loop(session_id: str, message: str):
    """Handles the chat and determines if human intervention is needed"""
    if session_id not in sessions:
        sessions[session_id] = {"conversation": [], "needs_human": False}
        logging.info(f"New session created: {session_id}")

    conversation = sessions[session_id]["conversation"]
    needs_human = sessions[session_id]["needs_human"]

    # Add user message to conversation history
    conversation.append({"role": "user", "content": message})

    # Check if the user is asking for a summary
    if "in 2 lines" in message.lower() or "summarize" in message.lower():
        summary = await summarize_text(conversation)
        conversation.append({"role": "assistant", "content": summary})
        logging.info(f"Generated summary for session {session_id}: {summary}")
        return summary, False

    # AI response
    try:
        response = ai_assistant.generate_reply(messages=conversation)
    except Exception as e:
        logging.error(f"Error generating AI response for session {session_id}: {str(e)}")
        response = "An error occurred while processing your request. Please try again."

    # Add AI response to conversation history
    conversation.append({"role": "assistant", "content": response})

    # Simulate need for human intervention
    needs_human = "help" in message.lower() or "human" in message.lower()
    sessions[session_id]["needs_human"] = needs_human

    if needs_human:
        logging.info(f"Human intervention requested for session {session_id}")
        return "A human agent will assist you shortly.", True

    return response, False

@app.post("/chat")
async def chat(session_id: str, user_message: str):
    """REST API Chat endpoint with session management"""
    if session_id not in sessions:
        sessions[session_id] = []  # Initialize conversation history for this session
    response, needs_human = await chat_with_human_in_loop(session_id, user_message)
    return {"response": response, "human_intervention": needs_human}


@app.get("/human-status")
async def human_status(session_id: str):
    """Check if human intervention is needed for a session"""
    return {"human_available": sessions.get(session_id, {}).get("needs_human", False)}


@app.post("/human-response")
async def human_response(session_id: str, human_message: str):
    """Handle human intervention for a session"""
    if session_id in sessions:
        sessions[session_id]["needs_human"] = False  # Reset human intervention flag
        sessions[session_id]["conversation"].append({"role": "human", "content": human_message})
        return {"status": "Human response recorded successfully.", "response": human_message}
    return {"status": "Session not found."}


async def chat_with_human_in_loop(session_id: str, message: str):
    """Handles the chat and determines if human intervention is needed"""
    if session_id not in sessions:
        sessions[session_id] = {"conversation": [], "needs_human": False}

    conversation = sessions[session_id]["conversation"]
    needs_human = sessions[session_id]["needs_human"]

    # Add user message to conversation history
    conversation.append({"role": "user", "content": message})

    # Check if the user is asking for a summary
    if "in 2 lines" in message.lower() or "summarize" in message.lower():
        summary = await summarize_text(conversation)
        conversation.append({"role": "assistant", "content": summary})
        return summary, False

    # AI response
    response = ai_assistant.generate_reply(messages=conversation)

    # Add AI response to conversation history
    conversation.append({"role": "assistant", "content": response})

    # Simulate need for human intervention (you can modify the logic)
    needs_human = "help" in message.lower() or "human" in message.lower()
    sessions[session_id]["needs_human"] = needs_human

    if needs_human:
        return "A human agent will assist you shortly.", True

    return response, False


async def summarize_text(conversation: list) -> str:
    """Summarize the conversation history"""
    prompt = "Summarize the following conversation in 2 lines:\n\n"
    for msg in conversation:
        prompt += f"{msg['role']}: {msg['content']}\n"
    summary = ai_assistant.generate_reply(messages=[{"role": "user", "content": prompt}])
    return summary if isinstance(summary, str) else summary.get("content", "Unable to summarize.")

# Serve the index.html file
@app.get("/")
async def get():
    # Get the path to the index.html file
    file_path = os.path.join(os.path.dirname(__file__), "app\\views\\index.html")
    
    # Read the file content
    with open(file_path, "r") as file:
        html_content = file.read()
    
    # Return the HTML content
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    