from app.services.research_service import AutoGenResearchSession

research_service = AutoGenResearchSession()

async def start_research(request, background_tasks):
    return await research_service.start_research(request, background_tasks)

async def get_research_status(session_id):
    return await research_service.get_research_status(session_id)

async def get_pending_input(session_id):
    return await research_service.get_pending_input(session_id)

async def submit_human_input(input_data):
    return await research_service.submit_human_input(input_data)

async def get_research_messages(session_id):
    return await research_service.get_research_messages(session_id)