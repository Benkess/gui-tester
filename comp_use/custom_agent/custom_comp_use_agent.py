# Custom LangGraph Computer Use Example

# Import necessary libraries
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages.utils import trim_messages
import base64
import json

# Library Imports
import os
import sys
from agent_logger import AgentLogger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) # Adjust path for imports
# Import core Assistant base class
from comp_use_env import ComputerUseEnv

# Global Constants
DEFAULT_SYSTEM_PROMPT = "You are controlling a computer. The user will give you instructions and you can use tools to interact with the computer."
DEFAULT_TOOL_CHOICE = "required" # LLM must call a tool, if it doesn't the agent will respond with an error message and try again
DEFAULT_MAX_TOOL_CALLING_ITERATIONS = 100
DEFAULT_TRIM_STRATEGY = "last"
DEFAULT_TOKEN_COUNTER = "approximate"
DEFAULT_MAX_TOKENS = 16384
DEFAULT_START_ON = "human" # This will be a screenshot message
DEFAULT_INCLUDE_SYSTEM = True
DEFAULT_ALLOW_PARTIAL = False
# =============================================================================
# STATE DEFINITION
# =============================================================================


def format_tool_output_for_log(content: Any) -> Any:
    """Return a log-safe representation of tool output without changing stored state."""
    if not isinstance(content, str):
        return content

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return content

    result = parsed.get("result")
    if isinstance(result, str) and result.startswith("data:image/png;base64,"):
        parsed["result"] = "<screenshot image omitted>"
        return json.dumps(parsed)

    return content

class AgentState(TypedDict):
    """
    State object that flows through the LangGraph nodes.

    Fields:
    - messages: Chat history with add_messages reducer (list of AnyMessage)
    - step_count: Current step number
    - should_exit: Boolean flag indicating if agent should exit. (Move to END node if True)
    """
    messages: Annotated[list[AnyMessage], add_messages]
    step_count: int
    should_exit: bool

# =============================================================================
# COMPUTER USE AGENT IMPLEMENTATION
# =============================================================================

class ComputerUseAgent():
    """
    Computer Use Agent:
        This is a LangGraph based computer use agent. It expects to receive a ComputerUseEnv instance 
        which will contain the computer use tool and screenshot functionality. It supports other tool 
        use and expects LangChain compatible tools. It supports any OpenAI API compatible computer 
        use model. The agent stores a static system prompt and user instruction. The remainder of the 
        chat history will use sliding window context management.  
    """

    def __init__(
        self,
        model: str,
        computer_use_env: ComputerUseEnv,
        user_prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        tools: list | None = None,
        tool_choice: str = DEFAULT_TOOL_CHOICE,
        max_tool_calling_iterations: int = DEFAULT_MAX_TOOL_CALLING_ITERATIONS,
        api_key: str | None = None,
        base_url: str | None = None,
        api_key_env: str | None = None,
        trim_strategy: str = DEFAULT_TRIM_STRATEGY,
        token_counter: str | Any = DEFAULT_TOKEN_COUNTER,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        start_on: str = DEFAULT_START_ON,
        include_system: bool = DEFAULT_INCLUDE_SYSTEM,
        allow_partial: bool = DEFAULT_ALLOW_PARTIAL,
        include_user_prompt_in_image_message: bool = False,
        verbose: bool = False,
        log_file: str | None = None
    ) -> None:
        """
        Initialize the ComputerUseAgent.

        Args:
            model (str): The OpenAI model to use (e.g., "gpt-5.4").
            computer_use_env (ComputerUseEnv): An instance of the ComputerUseEnv class that provides the computer use tool and screenshot functionality.
            user_prompt (str): The initial user instruction to the agent.
            system_prompt (str, optional): Custom system prompt to use instead of the default. Defaults to DEFAULT_SYSTEM_PROMPT.
            tools (list, optional): A list of additional LangChain compatible tools to provide to the agent. Defaults to None.
            tool_choice (str, optional): The tool choice strategy for the LLM. Defaults to DEFAULT_TOOL_CHOICE, which will use the agent's default (required). Options are:
                - `str` of the form `'<<tool_name>>'`: calls `<<tool_name>>` tool.
                - `'auto'`: automatically selects a tool (including no tool).
                - `'none'`: does not call a tool.
                - `'any'` or `'required'` or `True`: force at least one tool to be called.
                - `dict` of the form `{"type": "function", "function": {"name": <<tool_name>>}}`: calls `<<tool_name>>` tool.
                - `False` or `None`: no effect, default OpenAI behavior.
            max_tool_calling_iterations (int, optional): Maximum number of iterations for tool calling in a single LLM call to prevent infinite loops. Defaults to DEFAULT_MAX_TOOL_CALLING_ITERATIONS.
            trim_strategy (str, optional): Strategy for trimming messages when token limit is exceeded. Defaults to DEFAULT_TRIM_STRATEGY. Options are:
                - 'last': Keep the last messages within the token limit.
                - 'first': Keep the first messages within the token limit.
            token_counter:
                - "approximate": use LangChain's built-in approximate counting
                - "exact": create a ChatOpenAI token counter for this model
                - otherwise: pass a custom LangChain-compatible token counter object
            max_tokens (int, optional): Maximum number of tokens for the model context. Defaults to DEFAULT_MAX_TOKENS.
            start_on (str, optional): The type of message to start the conversation on. Defaults to DEFAULT_START_ON. Options are "human", "system", "ai", "tool" or a list of message type names.
            include_system (bool, optional): Whether to always include the system prompt in the messages sent to the LLM. Defaults to DEFAULT_INCLUDE_SYSTEM.
            allow_partial (bool, optional): Whether to allow partial responses from the LLM if the response exceeds the token limit after tool calls. If False, the agent will respond with an error message and try again with a trimmed message history. Defaults to DEFAULT_ALLOW_PARTIAL.
            api_key (str, optional): API key used with OpenAI API. Defaults to None, in which case it will look for the key in the environment variable specified by `api_key_env`.
            base_url (str, optional): Base URL for OpenAI API if using a compatible service. Defaults to None.
            api_key_env (str, optional): Environment variable name to look for the API key if `api_key` is not provided. Defaults to None.
            include_user_prompt_in_image_message (bool, optional): Whether to include the user prompt as text in the image message when sending the screenshot to the LLM. Defaults to False.
            verbose (bool, optional): Whether to print verbose debug information during the agent's operation. Defaults to False.
            log_file (str, optional): Path to write the run log. If None, logging is disabled. Defaults to None.
        """
        if not model:
            raise ValueError("Model must be specified")
        self.model = model
        if not computer_use_env:
            raise ValueError("ComputerUseEnv instance must be provided")
        self.computer_use_env = computer_use_env
        if not user_prompt:
            raise ValueError("User prompt must be specified")
        self.user_prompt = user_prompt

        # Customization parameters
        if tool_choice not in ['auto', 'none', 'any', 'required', True, False, None] and not (isinstance(tool_choice, str) and tool_choice.startswith('<<') and tool_choice.endswith('>>')) and not (isinstance(tool_choice, dict) and tool_choice.get("type") == "function" and "name" in tool_choice.get("function", {})):
            raise ValueError("Invalid tool_choice value")
        self.tool_choice = tool_choice
        self.max_tool_calling_iterations = max_tool_calling_iterations
        # self.system_prompt = system_prompt
        self.trim_strategy = trim_strategy
        self.max_tokens = max_tokens
        self.start_on = start_on
        self.include_system = include_system
        self.allow_partial = allow_partial
        resolved_api_key = api_key
        if not resolved_api_key and api_key_env:
            resolved_api_key = os.getenv(api_key_env)
        if not resolved_api_key and api_key_env:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                resolved_api_key = os.getenv(api_key_env)
            except ImportError as e:
                print(
                    "Warning: python-dotenv is not installed.\n"
                    "Install it with: pip install python-dotenv"
                )
                print(e)
        if not resolved_api_key:
            print("Warning: No API key provided. " \
            "Please provide an API key via the constructor, environment variable, or .env file.")
            raise ValueError("API key is required for the agent to function.")

        self.include_user_prompt_in_image_message = include_user_prompt_in_image_message
        self.verbose = verbose
        self.logger = AgentLogger(log_file)

        # ============================================
        # Static Message History Setup
        # ============================================

        self.static_messages = self._build_static_messages(system_prompt=system_prompt, user_prompt=user_prompt)

        # ============================================
        # Tool Mapping
        # ============================================

        computer_use_tool = self.computer_use_env.get_computer_use_tool()
        tools = [computer_use_tool] if tools is None else tools + [computer_use_tool]
        self.tool_map = {tool.name: tool for tool in tools}

        # ============================================
        # Create LLM with Tools
        # ============================================

        # Create LLM
        llm = ChatOpenAI(model=model, api_key=resolved_api_key, base_url=base_url)

        # Bind tools to LLM
        self.llm_with_tools = llm.bind_tools(tools, tool_choice=tool_choice)

        # ============================================
        # Create Exact Token Counter if specified
        # ============================================

        if token_counter == "approximate":
            self.trim_token_counter = "approximate"
        elif token_counter == "exact":
            self.trim_token_counter = ChatOpenAI(
                model=model,
                api_key=resolved_api_key,
                base_url=base_url,
            )
        else:
            self.trim_token_counter = token_counter

    def _build_static_messages(self, system_prompt: str, user_prompt: str) -> list[AnyMessage]:
        """
        Build the static part of the message history that will be included in every LLM call.

        This includes the system prompt and the initial user instruction. The system prompt can be customized via the constructor, and the user instruction is provided as a parameter.

        Returns:
            list[AnyMessage]: A list of messages representing the static message history.
        """
        return [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

    def get_initial_state(self) -> AgentState:
        """
        Define the initial state of the agent.
        {
            "messages": [],
            "step_count": 0,
            "should_exit": False
        }
        """
        return AgentState(
            messages = [],
            step_count = 0,
            should_exit = False
        )

    # =============================================================================
    # GRAPH CREATION
    # =============================================================================

    def create_graph(self, checkpointer=None):
        return self.create_graph_from_llm(self.llm_with_tools, checkpointer=checkpointer)

    def create_graph_from_llm(self, llm_with_tools, checkpointer=None):
        """
        Create LangGraph state machine for agent loop with tool calling. The graph will have the following nodes:
        1. capture_screenshot_node: Captures a screenshot and adds it to the messages.
        2. generate_action_node: Prompts the LLM for the next action. This node will also handle trimming messages and tool calling.
        3. route_after_response: Routes to END or back to generate_action_node.

        Args:
            llm_with_tools: The LLM with tools bound that will be used in the generate_action_node to get the agent's response and tool calls.
            checkpointer: Optional LangGraph checkpointer for saving and resuming state.
        """

        # =========================================================================
        # NODE: capture_screenshot_node
        # =========================================================================
        def capture_screenshot_node(state: AgentState) -> dict:
            """
            Node: capture_screenshot_node
            This node captures a screenshot of the computer environment and adds it to the messages. It also increments the step count.
            
            """
            step = state["step_count"] + 1

            print(f"\n{'='*60}")
            print(f"STEP {step}")
            print(f"{'='*60}\n")
            print("[1/3] Capturing screenshot...")

            self.logger.log_step_start(step)

            image_bytes, mime_type = self.computer_use_env.capture_screenshot()
            if self.include_user_prompt_in_image_message:
                text = self.user_prompt
            else:
                text = None
            image_message = build_image_message(image_bytes, mime_type, text)

            self.logger.log_screenshot(mime_type)

            if self.verbose:
                print("Captured screenshot and created image message.")

            return {
                    "step_count": step,
                    "messages": [image_message]
                }
        
        # =========================================================================
        # NODE: generate_action_node
        # =========================================================================
        def generate_action_node(state: AgentState) -> dict:
            print("[2/3] Generating action...")

            if self.verbose:
                print("Calling LLM with messages...")
            
            messages = state["messages"]

            # Trim messages to avoid exceeding context window
            trimmed_messages = trim_messages(  
                messages,
                strategy=self.trim_strategy,
                token_counter=self.trim_token_counter,
                max_tokens=self.max_tokens,
                start_on=self.start_on,
                include_system=self.include_system,
                allow_partial=self.allow_partial,
            )
            resolved_messages = self.static_messages + trimmed_messages

            if self.verbose:
                print(f"Resolved messages = Static messages + Trimmed messages (max_tokens={self.max_tokens}):")
                for msg in resolved_messages:
                    # Print a summary of each message. Include type and full content for all content fields. For images include mime type but not the base64 content.
                    if isinstance(msg, HumanMessage):
                        content_summary = []
                        if isinstance(msg.content, str):
                            content_summary.append(f'Text: "{msg.content}"')
                        else:
                            for item in msg.content:
                                if isinstance(item, str):
                                    content_summary.append(f'Text: "{item}"')
                                elif isinstance(item, dict) and item.get("type") == "image":
                                    content_summary.append(f'Image: mime_type={item.get("mime_type")}')
                                else:
                                    content_summary.append(f"Unknown content type: {item}")
                        print(f"  HumanMessage: {', '.join(content_summary)}")
                    elif isinstance(msg, AIMessage):
                        print(f"  AIMessage: {msg.content}")
                    elif isinstance(msg, SystemMessage):
                        print(f"  SystemMessage: {msg.content}")
                    elif isinstance(msg, ToolMessage):
                        tool_content = format_tool_output_for_log(msg.content)
                        print(f"  ToolMessage: {tool_content}, tool_call_id={msg.tool_call_id}")

            # Agent loop for tool calling
            response = llm_with_tools.invoke(resolved_messages) # Pass the resolved messages = static + trimmed messages to the LLM with tools
            new_messages = []
            new_messages.append(response) # Add the LLM response to the new messages list. This will be added to the state messages when returned from the node.

            should_exit = False
            if response.tool_calls:
                print("[3/3] Executing actions...")

                if self.verbose:
                    print(f"LLM wants to call {len(response.tool_calls)} tool(s)")

                for tool_call in response.tool_calls:
                    function_name = tool_call["name"]
                    function_args = tool_call["args"]

                    # Always show thought + action in console (not just verbose)
                    thought = function_args.get("thought")
                    if thought:
                        print(f"  Thought: {thought}")
                    action_parts = [f"{k}={v}" for k, v in function_args.items() if k != "thought" and v is not None]
                    print(f"  Action : {function_name}  {' '.join(action_parts)}")

                    if self.verbose:
                        print(f"  Tool: {function_name}")
                        print(f"  Args: {function_args}")

                    if function_name in self.tool_map:
                        result = self.tool_map[function_name].invoke(function_args)
                    else:
                        result = f"Error: Unknown function {function_name}"

                    if self.verbose:
                        result_summary = format_tool_output_for_log(result)
                        print(f"  Result: {result_summary}")

                    # self.logger.log_tool_call(function_name, function_args, result)

                    terminal = False
                    # tool_message_content = result
                    result_parsed = json.loads(result) if isinstance(result, str) else result
                    if isinstance(result_parsed, dict):
                        terminal = bool(result_parsed.get("terminal", False))
                    if terminal:
                        should_exit = True
                        # Note: This does not break the loop so other tools may run after this. Later we may want to access tool_message_content for a final message or something like that.

                    new_messages.append(ToolMessage(
                        content=result,
                        tool_call_id=tool_call["id"]
                    ))

                self.logger.log_new_messages(new_messages)

            else:
                # No more tool calls, final answer
                print("[3/3] Final response received (no tool calls).")
                print(f"\nAgent Final Response: {response.content}\n")
                should_exit = True
                self.logger.log_new_messages(new_messages)
                print(f"\n{'='*60}")
                print(f"AGENT FINISHED:")
                print(f"{'='*60}\n")

            if not should_exit and state["step_count"] >= self.max_tool_calling_iterations:
                print(f"Reached maximum tool calling iterations ({self.max_tool_calling_iterations}). Exiting to prevent infinite loop.")
                should_exit = True
            
            return {
                    "messages": new_messages,
                    "should_exit": should_exit
                }
        
        # =========================================================================
        # ROUTING FUNCTION
        # =========================================================================
        def route_after_generation(state: AgentState) -> str:
            if state["should_exit"]:
                return END
            else:
                return "capture_screenshot_node"

        # =========================================================================
        # GRAPH CONSTRUCTION
        # =========================================================================
        graph_builder = StateGraph(AgentState)

        graph_builder.add_node("capture_screenshot_node", capture_screenshot_node)
        graph_builder.add_node("generate_action_node", generate_action_node)

        graph_builder.add_edge(START, "capture_screenshot_node")
        graph_builder.add_edge("capture_screenshot_node", "generate_action_node")
        graph_builder.add_conditional_edges(
            "generate_action_node",
            route_after_generation,
            {
                "capture_screenshot_node": "capture_screenshot_node",
                END: END
            }
        )

        graph = graph_builder.compile(checkpointer=checkpointer)
        return graph
    
    def run(self, env_type: str = "unknown", start_url: str | None = None, headless: bool = False, log_path: str | None = None):
        thread_id = f"computer_use_agent_thread"
        config = {"configurable": {"thread_id": thread_id}}

        self.logger.log_run_start(
            task=self.user_prompt,
            model=self.model,
            env_type=env_type,
            log_path=log_path,
            start_url=start_url,
            headless=headless,
            starting_messages=self.static_messages,
        )

        print("Creating LangGraph...")
        graph = self.create_graph()
        print("Graph created successfully!")
        state = self.get_initial_state()
        try:
            final_state = graph.invoke(state, config=config)
            all_messages = self.static_messages + final_state.get("messages", [])
            self.logger.log_run_end(all_messages)
        finally:
            self.logger.close()

def build_image_message(image_bytes: bytes, mime_type: str, text: str | None = None) -> HumanMessage:
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    if text is None:
        return HumanMessage(
            content=[
                {
                    "type": "image",
                    "base64": encoded_image,
                    "mime_type": mime_type,
                    "detail": "original",
                },
            ]
        )
    else:
        return HumanMessage(
            content=[
                {"type": "text", "text": text},
                {
                    "type": "image",
                    "base64": encoded_image,
                    "mime_type": mime_type,
                    "detail": "original",
                },
            ]
        )
    

# End of file
