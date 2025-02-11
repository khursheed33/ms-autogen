from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from app.models.research_models import ResearchRequest, HumanInput
from app.services.research_service import AutoGenResearchSession

app = FastAPI()
router = APIRouter()

# Initialize the research service
research_service = AutoGenResearchSession()

@router.post("/research/start")
async def start_research_endpoint(request: ResearchRequest, background_tasks: BackgroundTasks):
    return await research_service.start_research(request, background_tasks)

@router.get("/research/{session_id}/status")
async def get_research_status_endpoint(session_id: str):
    return await research_service.get_research_status(session_id)

@router.get("/research/{session_id}/pending-input")
async def get_pending_input_endpoint(session_id: str):
    return await research_service.get_pending_input(session_id)

@router.post("/research/input")
async def submit_human_input_endpoint(input_data: HumanInput):
    return await research_service.submit_human_input(input_data)

@router.get("/research/{session_id}/messages")
async def get_research_messages_endpoint(session_id: str):
    return await research_service.get_research_messages(session_id)

# Include the router in the app
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)