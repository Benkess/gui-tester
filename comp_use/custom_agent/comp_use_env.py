# Computer Use Environment

# Imports
from abc import ABC, abstractmethod
from typing import Tuple, Any, Protocol, runtime_checkable

@runtime_checkable
class LangChainToolLike(Protocol):
    name: str
    def invoke(self, input: Any, config: Any | None = None) -> Any: ...


# Computer Use Environment
class ComputerUseEnv(ABC):
    """
    Lifecycle note:
    The ComputerUseAgent does not call start_env() or stop_env().
    The caller is responsible for launching and shutting down the environment.
    """
    
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def start_env(self):
        """
        Start the computer use environment. When this returns it should be valid to call handle_computer_actions and capture_screenshot.
        """
        pass

    @abstractmethod
    def stop_env(self):
        """
        Stop the computer use environment and clean up any resources.
        """
        pass

    @abstractmethod
    def get_computer_use_tool(self) -> LangChainToolLike:
        """
        Get a function that can be used as a tool for the agent to interact with the computer environment. 
        Must return a langchain compatible tool function.

        Returns:
            function: A LangChain-compatible tool used to control this environment.
        """
        pass

    @abstractmethod
    def capture_screenshot(self) -> Tuple[bytes, str]:
        """
        Capture a screenshot of the current state of the computer environment.

        Returns:
            image_bytes (bytes): The captured screenshot in bytes format
            mime_type (str): The MIME type of the captured screenshot (e.g., 'image/png')
        """
        pass


class InvalidActionError(Exception):
    """Custom exception for invalid actions in the computer use environment."""
    pass


