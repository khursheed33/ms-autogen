import autogen

def create_human_proxy_agent(config_list):
    return autogen.UserProxyAgent(
        name="human_proxy",
        human_input_mode="ALWAYS",
        max_consecutive_auto_reply=1,
        code_execution_config={"use_docker": False},
        system_message="You are a human proxy for research validation."
    )