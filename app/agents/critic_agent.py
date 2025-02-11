import autogen

def create_critic_agent(config_list):
    return autogen.AssistantAgent(
        name="critic",
        llm_config={
            "config_list": config_list,
            "temperature": 0.7,
        },
        system_message="You are a critical reviewer who evaluates research quality."
    )