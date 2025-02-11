import autogen

def create_researcher_agent(config_list):
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