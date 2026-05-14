from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from .agent import chat_with_agent
from langchain_core.messages import HumanMessage, AIMessage
import uvicorn
import traceback

app = FastAPI(title="Tailor Talk Backend")

@app.get("/")
async def root():
    return {"message": "Tailor Talk Backend is running!"}

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []
    folder_id: Optional[str] = None
    local_path: Optional[str] = None
    mode: str = "drive" # "drive" or "system"
    model_name: Optional[str] = None
    custom_api_key: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    history: List[dict]

def format_history(history_dicts):
    formatted = []
    for h in history_dicts:
        if h['role'] == 'user':
            formatted.append(HumanMessage(content=h['content']))
        else:
            formatted.append(AIMessage(content=h['content']))
    return formatted

def deformat_history(history_messages):
    deformatted = []
    for m in history_messages:
        if isinstance(m, HumanMessage):
            role = 'user'
        elif isinstance(m, AIMessage):
            role = 'assistant'
        else:
            role = 'assistant' # Default for others
            
        content = m.content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'text':
                    text_parts.append(part.get('text', ''))
                elif isinstance(part, str):
                    text_parts.append(part)
            content_text = "".join(text_parts)
        else:
            content_text = str(content)
        deformatted.append({'role': role, 'content': content_text})
    return deformatted

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        from .drive_service import drive_service, local_service
        if request.mode == "drive" and request.folder_id:
            drive_service.folder_id = request.folder_id
        elif request.mode == "system" and request.local_path:
            local_service.root_path = request.local_path
            
        history = format_history(request.history)
        # Add a system message to the history to tell the agent the current mode
        mode_context = f"Current Mode: {request.mode.upper()}. "
        if request.mode == "drive":
            mode_context += f"Searching in Drive Folder ID: {request.folder_id}"
        else:
            mode_context += f"Searching in Local Path: {request.local_path}"
        
        full_message = f"{mode_context}\n\nUser Message: {request.message}"
        
        # Clean and log the custom API key status (safe logging)
        custom_key = request.custom_api_key.strip() if request.custom_api_key else None
        if custom_key:
            print(f"Received custom API key (Length: {len(custom_key)})")
        
        response_text, updated_history = chat_with_agent(
            full_message, 
            history, 
            model_name=request.model_name,
            api_key=custom_key
        )
        return ChatResponse(
            response=response_text,
            history=deformat_history(updated_history)
        )
    except Exception as e:
        print(f"Backend Error in /chat: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/folders")
async def get_folders():
    try:
        from .drive_service import drive_service
        folders = drive_service.list_folders()
        if isinstance(folders, str):
            raise HTTPException(status_code=500, detail=folders)
        return {"folders": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
