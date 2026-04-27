# Computer Use Agent Launch
# Load configs specifying the custom computer use agent and environment, then launch the agent.

# Imports
import json
from custom_comp_use_agent import ComputerUseAgent
from comp_use_env import ComputerUseEnv

class ComputerUseEnvLoader:
    """
    ComputerUseEnvLoader is responsible for loading and initializing a ComputerUseEnv instance based on a provided configuration. 
    The configuration should specify the type of environment to load and any necessary parameters for initialization.
    """
    def __init__(self, config_path: str):
        self.config_path = config_path

    def load_env(self) -> ComputerUseEnv:
        # Load the environment configuration from the specified path
        with open(self.config_path, 'r') as f:
            env_config = json.load(f)
        
        env_type = env_config.get("type")
        env_params = env_config.get("params", {})

        # Based on the type, initialize the appropriate ComputerUseEnv subclass
        if env_type == "playwright":
            from playwright_env import PlaywrightComputerUseEnv
            return PlaywrightComputerUseEnv(**env_params)
        elif env_type == "pyautogui":
            from pyautogui_env import PyAutoGUIComputerUseEnv
            return PyAutoGUIComputerUseEnv(**env_params)
        else:
            raise ValueError(f"Unsupported environment type: {env_type}")
        
class ComputerUseAgentLoader:
    """
    ComputerUseAgentLoader is responsible for loading and initializing a ComputerUseAgent instance based on a provided configuration. 
    The configuration should specify the parameters for the agent, including model, system prompt, user prompt, and any other relevant settings.
    """
    def __init__(self, config_path: str):
        self.config_path = config_path

    def load_agent(self, env: ComputerUseEnv) -> ComputerUseAgent:
        # Load the agent configuration from the specified path
        with open(self.config_path, 'r') as f:
            raw_agent_config = json.load(f)

        # The config file may have the shape {"name": "...", "agent": {...}}.
        # ComputerUseAgent only accepts the inner "agent" dict.
        agent_config = raw_agent_config.get("agent", raw_agent_config)

        # "implementation" is a config-file convention, not a ComputerUseAgent parameter.
        agent_config.pop("implementation", None)
        
        # Initialize the ComputerUseAgent with the loaded configuration and provided environment
        return ComputerUseAgent(computer_use_env=env, **agent_config)
    
def launch_computer_use_agent(env_config_path: str, agent_config_path: str):
    # Load the environment
    env_loader = ComputerUseEnvLoader(env_config_path)
    env = env_loader.load_env()
    env.start_env()

    # Load the agent with the environment
    agent_loader = ComputerUseAgentLoader(agent_config_path)
    agent = agent_loader.load_agent(env)

    # Run the agent
    try:
        agent.run()
    finally:
        env.stop_env()
