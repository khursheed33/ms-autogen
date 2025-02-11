import os
import asyncio
import uuid
from datetime import datetime
import autogen
from fastapi import HTTPException
from typing import Optional, Dict, List

class AutoGenResearchSession:
    def __init__(self):
        self.research_sessions: Dict[str, Dict] = {}  # Stores active research sessions
        self.pending_inputs: Dict[str, Dict] = {}    # Stores pending human inputs

    def _create_researcher_agent(self, config_list):
        """Create and return the researcher agent."""
        return autogen.AssistantAgent(
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

    def _create_human_proxy_agent(self, config_list):
        """Create and return the human proxy agent."""
        human_proxy = autogen.UserProxyAgent(
            name="human_proxy",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=1,
            code_execution_config={"use_docker": False},
            system_message="You are a human proxy for research validation."
        )

        # Override the human proxy's get_human_input method
        async def get_human_input(prompt: str) -> str:
            input_id = str(uuid.uuid4())
            self.pending_inputs[input_id] = {
                "session_id": self.session_id,
                "prompt": prompt,
                "response": None,
                "timestamp": datetime.now().isoformat()
            }
            
            # Wait for human input (with timeout)
            timeout = 300  # 5 minutes timeout
            start_time = datetime.now()
            while not self.pending_inputs[input_id]["response"]:
                if (datetime.now() - start_time).seconds > timeout:
                    del self.pending_inputs[input_id]
                    raise TimeoutError("No human input received within timeout period")
                await asyncio.sleep(1)
            
            response = self.pending_inputs[input_id]["response"]
            del self.pending_inputs[input_id]
            return response

        human_proxy.get_human_input = get_human_input
        return human_proxy

    def _create_critic_agent(self, config_list):
        """Create and return the critic agent."""
        return autogen.AssistantAgent(
            name="critic",
            llm_config={
                "config_list": config_list,
                "temperature": 0.7,
            },
            system_message="You are a critical reviewer who evaluates research quality."
        )

    async def start_research(self, request, background_tasks):
        """Start a new research session."""
        session_id = str(uuid.uuid4())
        config_list = [
            {
                'model': 'gpt-4',
                'api_key': os.getenv("OPENAI_API_KEY")  # Replace with actual API key
            }
        ]

        # Initialize agents
        researcher = self._create_researcher_agent(config_list)
        human = self._create_human_proxy_agent(config_list)
        critic = self._create_critic_agent(config_list)

        # Store session
        self.research_sessions[session_id] = {
            "session_id": session_id,
            "status": "initializing",
            "researcher": researcher,
            "human": human,
            "critic": critic,
            "messages": []
        }

        # Start research in background
        background_tasks.add_task(
            self._run_research,
            session_id,
            request.topic,
            request.initial_context
        )
        
        return {
            "session_id": session_id,
            "status": "initialized",
            "message": "Research session started"
        }

    async def _run_research(self, session_id: str, topic: str, initial_context: Optional[str] = None):
        """Run the research process."""
        session = self.research_sessions[session_id]
        session["status"] = "in_progress"

        groupchat = autogen.GroupChat(
            agents=[session["researcher"], session["human"], session["critic"]],
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
            # Run research
            await asyncio.get_event_loop().run_in_executor(
                None,
                manager.initiate_chat,
                session["researcher"],
                research_prompt
            )
            session["status"] = "completed"
        except Exception as e:
            session["status"] = "error"
            raise HTTPException(status_code=500, detail=str(e))

    async def get_research_status(self, session_id: str):
        """Get the status of a research session."""
        if session_id not in self.research_sessions:
            raise HTTPException(status_code=404, detail="Research session not found")
        
        session = self.research_sessions[session_id]
        return {
            "session_id": session_id,
            "status": session["status"],
            "pending_input": any(
                input["session_id"] == session_id 
                for input in self.pending_inputs.values()
            )
        }

    async def get_pending_input(self, session_id: str):
        """Get pending human input for a session."""
        pending = [
            {"input_id": input_id, **input_data}
            for input_id, input_data in self.pending_inputs.items()
            if input_data["session_id"] == session_id
        ]
        
        if not pending:
            raise HTTPException(
                status_code=404,
                detail="No pending inputs for this session"
            )
        
        return pending[0]

    async def submit_human_input(self, input_data):
        """Submit human input for a pending request."""
        pending = [
            input_id
            for input_id, data in self.pending_inputs.items()
            if data["session_id"] == input_data.session_id
        ]
        
        if not pending:
            raise HTTPException(
                status_code=404,
                detail="No pending input request found"
            )
        
        self.pending_inputs[pending[0]]["response"] = input_data.input
        
        return {"status": "success", "message": "Input received"}

    async def get_research_messages(self, session_id: str):
        """Get messages from a research session."""
        if session_id not in self.research_sessions:
            raise HTTPException(status_code=404, detail="Research session not found")
        
        session = self.research_sessions[session_id]
        return {
            "session_id": session_id,
            "messages": session["messages"]
        }