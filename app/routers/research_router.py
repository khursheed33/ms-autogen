from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.research_models import ResearchRequest, HumanInput
from app.controllers.research_controller import start_research, get_research_status, get_pending_input, submit_human_input, get_research_messages

research_router:APIRouter = APIRouter()

@research_router.post("/research/start")
async def start_research_endpoint(request: ResearchRequest, background_tasks: BackgroundTasks):
    return await start_research(request, background_tasks)

@research_router.get("/research/{session_id}/status")
async def get_research_status_endpoint(session_id: str):
    return await get_research_status(session_id)

@research_router.get("/research/{session_id}/pending-input")
async def get_pending_input_endpoint(session_id: str):
    return await get_pending_input(session_id)

@research_router.post("/research/input")
async def submit_human_input_endpoint(input_data: HumanInput):
    return await submit_human_input(input_data)

@research_router.get("/research/{session_id}/messages")
async def get_research_messages_endpoint(session_id: str):
    return await get_research_messages(session_id)