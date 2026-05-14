import os
from typing import Annotated, List, TypedDict, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from .drive_service import drive_service, local_service
import threading

load_dotenv()

# Define the state for the agent
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

# Define tools for the agent
@tool
def search_drive(
    name: str = None, 
    mime_type: str = None, 
    full_text: str = None, 
    query: str = None
):
    """
    Search for files in Google Drive. 
    You can search by name (partial match), mime_type (e.g., 'application/pdf', 'image/jpeg', 'application/vnd.google-apps.document'), 
    full_text (content inside the file), or a complex query string.
    """
    results = drive_service.search_files(query_string=query, name=name, mime_type=mime_type, full_text=full_text)
    if isinstance(results, str):
        return results
    if not results:
        return "No files found matching your criteria."
    
    formatted_results = []
    for f in results:
        formatted_results.append(
            f"Name: {f['name']}\nType: {f['mimeType']}\nLink: {f.get('webViewLink', 'N/A')}\nID: {f['id']}\n---"
        )
    return "\n".join(formatted_results)

@tool
def get_file_info(file_id: str):
    """Get detailed information about a specific file using its ID."""
    info = drive_service.get_file_metadata(file_id)
    if isinstance(info, str):
        return info
    if not info:
        return "File not found."
    return f"Name: {info['name']}\nType: {info['mimeType']}\nModified: {info['modifiedTime']}\nSize: {info.get('size', 'Unknown')} bytes\nLink: {info.get('webViewLink', 'N/A')}"

@tool
def search_local_system(query: str = None, name: str = None):
    """
    Search for files in the local system directory. 
    Use this if the user wants to search files on their local computer/system drive.
    """
    results = local_service.search_files(query=query, name=name)
    if isinstance(results, str):
        return results
    if not results:
        return "No local files found."
    
    formatted = []
    for f in results:
        formatted.append(f"Name: {f['name']}\nPath: {f['path']}\n---")
    return "\n".join(formatted)

@tool
def get_local_file_info(file_path: str):
    """Get detailed information about a local file using its full path."""
    info = local_service.get_file_metadata(file_path)
    if isinstance(info, str):
        return info
    return f"Name: {info['name']}\nPath: {info['path']}\nModified: {info['modifiedTime']}\nSize: {info['size']} bytes"

# Global tools list
agent_tools = [search_drive, get_file_info, search_local_system, get_local_file_info]

# Setup the LLM cache
_llm_cache = {}
_llm_cache_lock = threading.Lock()

def get_llm(model_name: str = None, api_key: str = None):
    global _llm_cache
    if not model_name:
        model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    
    # Create a unique cache key based on model and API key
    custom_key_clean = api_key.strip() if api_key and api_key.strip() else None
    effective_api_key = custom_key_clean if custom_key_clean else os.getenv("GOOGLE_API_KEY")
    
    # Use a truncated version of the key for the cache index to avoid storing the full key in logs/memory as a key
    key_hash = str(hash(effective_api_key))[-8:]
    cache_key = f"{model_name}_{key_hash}"
    
    with _llm_cache_lock:
        if cache_key in _llm_cache:
            return _llm_cache[cache_key]
        
        print(f"Initializing LLM with model: {model_name} (Custom Key: {bool(api_key)})")
        
        llm = ChatGoogleGenerativeAI(
            model=model_name, 
            google_api_key=effective_api_key,
            temperature=0,
            max_retries=3,
            model_kwargs={"transport": "rest"}
        )
        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(agent_tools)
        
        _llm_cache[cache_key] = llm_with_tools
        return llm_with_tools

# Define nodes
def call_model(state: AgentState, config: RunnableConfig = None):
    messages = state['messages']
    # Safely get model_name from config
    model_name = None
    if config:
        configurable = config.get("configurable", {})
        model_name = configurable.get("model_name")
        api_key = configurable.get("api_key")
    
    llm_instance = get_llm(model_name, api_key)
    
    key_status = "Custom" if api_key else "Default"
    print(f"Calling model {model_name or 'default'} with {len(messages)} messages. Key: {key_status}")
    for i, m in enumerate(messages):
        print(f"  Msg {i} ({type(m).__name__}): {str(m.content)[:50]}...")
    
    response = llm_instance.invoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# Construct the graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(agent_tools))

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

agent_executor = workflow.compile()

def chat_with_agent(user_input: str, history: List[BaseMessage] = [], model_name: str = None, api_key: str = None):
    system_msg = SystemMessage(content=(
        "You are 'Tailor Talk'. Goal: Find files. "
        "1. Use tools ONCE. "
        "2. If results found, list them concisely and STOP. "
        "3. If nothing found, say 'No files found' and STOP. "
        "4. NO loops. NO conversation. Be extremely brief."
    ))
    
    # Extreme history trimming to save quota (only last exchange)
    trimmed_history = history[-2:]
    messages = [system_msg] + trimmed_history + [HumanMessage(content=user_input)]
    
    print(f"Executing agent ({model_name or 'default'}) with {len(messages)} messages...")
    try:
        # Add recursion limit and custom config
        result = agent_executor.invoke(
            {"messages": messages}, 
            config={
                "recursion_limit": 5, 
                "configurable": {"model_name": model_name, "api_key": api_key}
            }
        )
        
        # Extract response content and ensure it's a string
        response_msg = result["messages"][-1]
        content = response_msg.content
        
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'text':
                    text_parts.append(part.get('text', ''))
                elif isinstance(part, str):
                    text_parts.append(part)
            response_text = "".join(text_parts)
        else:
            response_text = str(content)
            
        return response_text, result["messages"]
    except Exception as e:
        error_msg = str(e).lower()
        if "recursion" in error_msg:
            response_text = "I've reached my processing limit for this request. Please try a simpler search."
        elif "quota" in error_msg or "exhausted" in error_msg or "429" in error_msg:
            response_text = "Quota Limit Reached: This Gemini version has reached its free limit. Please switch to another model or try again in a few minutes."
        elif "not_found" in error_msg or "404" in error_msg:
            response_text = "Model Unavailable: This version of Gemini is currently not accessible. Please select a different version."
        else:
            response_text = "Something went wrong while processing your request. Please try again or switch models."
        
        # Return the error message and the original history + a fake AI message for the error
        return response_text, history + [AIMessage(content=response_text)]
