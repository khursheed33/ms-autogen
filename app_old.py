# app.py
import os
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import autogen
import asyncio
import json
import uuid
from datetime import datetime

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active research sessions
research_sessions = {}
# Store pending human inputs
pending_inputs = {}

class ResearchRequest(BaseModel):
    topic: str
    initial_context: Optional[str] = None

class HumanInput(BaseModel):
    session_id: str
    input: str

class AutoGenResearchSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = []
        self.status = "initializing"
        
        # Configure agents
        config_list = [
            {
                'model': 'gpt-4o-mini',
                'api_key': os.getenv("OPENAI_API_KEY")  # Replace with actual API key
            }
        ]

        # Configure researcher agent
        self.researcher = autogen.AssistantAgent(
            name="researcher",
            llm_config={
                "config_list": config_list,
                "temperature": 0.7,
            },
            system_message="""You are a news researcher assistant. Your role is to:
            1. Analyze news topics
            2. Gather relevant information
            3. Verify sources
            4. Create comprehensive summaries"""
        )

        # Configure human proxy agent
        self.human = autogen.UserProxyAgent(
            name="human_proxy",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=1,
            code_execution_config={"use_docker": False},
            system_message="You are a human proxy for research validation."
        )

        # Configure critic agent
        self.critic = autogen.AssistantAgent(
            name="critic",
            llm_config={
                "config_list": config_list,
                "temperature": 0.7,
            },
            system_message="You are a critical reviewer who evaluates research quality."
        )

        # Override human proxy's get_human_input
        async def get_human_input(prompt: str) -> str:
            input_id = str(uuid.uuid4())
            pending_inputs[input_id] = {
                "session_id": self.session_id,
                "prompt": prompt,
                "response": None,
                "timestamp": datetime.now().isoformat()
            }
            
            # Wait for human input (with timeout)
            timeout = 300  # 5 minutes timeout
            start_time = datetime.now()
            while not pending_inputs[input_id]["response"]:
                if (datetime.now() - start_time).seconds > timeout:
                    del pending_inputs[input_id]
                    raise TimeoutError("No human input received within timeout period")
                await asyncio.sleep(1)
            
            response = pending_inputs[input_id]["response"]
            del pending_inputs[input_id]
            return response

        self.human.get_human_input = get_human_input

    async def start_research(self, topic: str, initial_context: Optional[str] = None):
        self.status = "in_progress"
        
        groupchat = autogen.GroupChat(
            agents=[self.researcher, self.human, self.critic],
            messages=[],
            max_round=12
        )
        manager = autogen.GroupChatManager(groupchat=groupchat)

        research_prompt = f"""
        Research topic: "{topic}"
        {f'Additional context: {initial_context}' if initial_context else ''}
        
        Please follow this process:
        1. Create a research plan
        2. Gather initial information
        3. Wait for human validation
        4. Analyze and summarize findings
        5. Get final human approval
        """

        try:
            # Run research in background
            await asyncio.get_event_loop().run_in_executor(
                None,
                manager.initiate_chat,
                self.researcher,
                research_prompt
            )
            self.status = "completed"
        except Exception as e:
            self.status = "error"
            raise e

# API Endpoints
@app.post("/research/start")
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid.uuid4())
    session = AutoGenResearchSession(session_id)
    research_sessions[session_id] = session
    
    # Start research in background
    background_tasks.add_task(
        session.start_research,
        request.topic,
        request.initial_context
    )
    
    return {
        "session_id": session_id,
        "status": "initialized",
        "message": "Research session started"
    }

@app.get("/research/{session_id}/status")
async def get_research_status(session_id: str):
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Research session not found")
    
    session = research_sessions[session_id]
    return {
        "session_id": session_id,
        "status": session.status,
        "pending_input": any(
            input["session_id"] == session_id 
            for input in pending_inputs.values()
        )
    }

@app.get("/research/{session_id}/pending-input")
async def get_pending_input(session_id: str):
    pending = [
        {"input_id": input_id, **input_data}
        for input_id, input_data in pending_inputs.items()
        if input_data["session_id"] == session_id
    ]
    
    if not pending:
        raise HTTPException(
            status_code=404,
            detail="No pending inputs for this session"
        )
    
    return pending[0]

@app.post("/research/input")
async def submit_human_input(input_data: HumanInput):
    # Find relevant pending input
    pending = [
        input_id
        for input_id, data in pending_inputs.items()
        if data["session_id"] == input_data.session_id
    ]
    
    if not pending:
        raise HTTPException(
            status_code=404,
            detail="No pending input request found"
        )
    
    # Update pending input with response
    pending_inputs[pending[0]]["response"] = input_data.input
    
    return {"status": "success", "message": "Input received"}

@app.get("/research/{session_id}/messages")
async def get_research_messages(session_id: str):
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Research session not found")
    
    session = research_sessions[session_id]
    return {
        "session_id": session_id,
        "messages": session.messages
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)