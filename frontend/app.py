import streamlit as st
import os
from dotenv import load_dotenv

# Import backend logic directly for seamless deployment
from backend.agent import chat_with_agent
from backend.drive_service import drive_service, local_service
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

# Global Model Configuration
MODEL_OPTIONS = {
    "Gemini 3 Flash (Preview)": "gemini-3-flash-preview",
    "Gemini 3 Pro (Preview)": "gemini-3-pro-preview",
    "Gemini 3.1 Pro (Preview)": "gemini-3.1-pro-preview",
    "Gemini 2.0 Flash": "gemini-2.0-flash-001",
    "Gemini Flash (Latest)": "gemini-flash-latest",
    "Gemini Pro (Latest)": "gemini-pro-latest",
}

# Page Configuration
st.set_page_config(
    page_title="Tailor Talk | AI Drive Agent",
    page_icon="🔍",
    layout="centered"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    .main {
        background: #0f172a;
        color: #f8fafc;
    }
    .stTextInput > div > div > input {
        background-color: #1e293b;
        color: #f8fafc;
        border-radius: 10px;
        border: 1px solid #334155;
    }
    .stButton > button {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: transform 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.05);
        color: white;
    }
    .chat-bubble {
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 80%;
    }
    .user-bubble {
        background: #3b82f6;
        color: white;
        margin-left: auto;
    }
    .ai-bubble {
        background: #1e293b;
        color: #f8fafc;
        border: 1px solid #334155;
    }
    .title-container {
        text-align: center;
        padding: 2rem 0;
    }
    .gradient-text {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
    }
    [data-testid="stSidebar"] {
        min-width: 300px;
        max-width: 400px;
    }
    div.stMarkdown {
        word-wrap: break-word;
    }
    div[data-testid="stSelectbox"] > div {
        background-color: #1e293b;
        color: #f8fafc;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    .stSelectbox label {
        color: #94a3b8;
    }
    .premium-alert {
        background: #1e293b;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid #334155;
        border-left: 6px solid #f59e0b;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.4);
        animation: premiumSlide 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        overflow: hidden;
    }
    .premium-alert::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(45deg, transparent, rgba(245, 158, 11, 0.05));
        pointer-events: none;
    }
    @keyframes premiumSlide {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    .alert-title {
        color: #f59e0b;
        font-weight: 800;
        font-size: 1.2rem;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .critical-alert {
        background: #1e293b;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid #334155;
        border-left: 6px solid #ef4444;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        animation: premiumSlide 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .critical-title {
        color: #ef4444;
        font-weight: 800;
        font-size: 1.2rem;
        margin-bottom: 6px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# Title Section
st.markdown('<div class="title-container"><h1 class="gradient-text">Tailor Talk</h1><p style="color: #94a3b8;">Your Intelligent Google Drive Assistant</p></div>', unsafe_allow_html=True)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "custom_api_key" not in st.session_state:
    st.session_state.custom_api_key = ""

def display_premium_error(title, message, icon="⚠️", type="warning"):
    class_name = "premium-alert" if type == "warning" else "critical-alert"
    title_class = "alert-title" if type == "warning" else "critical-title"
    
    # Strip any potential JSON or object strings just in case
    clean_msg = str(message).split("{")[0].strip()
    
    st.markdown(f"""
    <div class="{class_name}">
        <div class="{title_class}">{icon} {title}</div>
        <div style="color: #94a3b8; font-size: 1rem; line-height: 1.5;">{clean_msg}</div>
    </div>
    """, unsafe_allow_html=True)

# --- AUTHENTICATION SCREEN ---
if not st.session_state.authenticated:
    st.write("") # Spacer
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container():
            st.markdown("""
                <style>
                .auth-card {
                    background: #1e293b;
                    padding: 30px;
                    border-radius: 20px;
                    border: 1px solid #334155;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
                }
                </style>
            """, unsafe_allow_html=True)
            
            auth_mode = st.tabs(["Login", "Sign Up"])
            
            with auth_mode[0]:
                u = st.text_input("Username", key="login_user")
                p = st.text_input("Password", type="password", key="login_pass")
                if st.button("🚀 Enter Tailor Talk", use_container_width=True):
                    if u and p: # Simple demo auth
                        st.session_state.authenticated = True
                        st.session_state.username = u
                        st.rerun()
                    else:
                        st.error("Please enter credentials")
            
            with auth_mode[1]:
                su_u = st.text_input("Choose Username", key="signup_user")
                su_e = st.text_input("Email", key="signup_email")
                su_p = st.text_input("Create Password", type="password", key="signup_pass")
                if st.button("✨ Create Account", use_container_width=True):
                    if su_u and su_p:
                        st.session_state.authenticated = True
                        st.session_state.username = su_u
                        st.success("Account created!")
                        st.rerun()
    st.stop()

# Sidebar for Setup Info
with st.sidebar:
    st.markdown(f"### Welcome, **{st.session_state.username}**")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.divider()
    st.title("⚙️ Settings")
    
    # Mode Selection
    search_mode = st.radio("Search Mode", ["Google Drive", "System Drive"], index=0)
    st.session_state.search_mode = "drive" if search_mode == "Google Drive" else "system"
    
    st.divider()
    
    # Sync functions for model selection
    def sync_sidebar():
        label = st.session_state.model_selector_sidebar_widget
        st.session_state.selected_model_label = label
        st.session_state.selected_model = MODEL_OPTIONS[label]
        # Cross-sync the bottom selector's key
        st.session_state.model_selector_bottom = label

    def sync_bottom():
        label = st.session_state.model_selector_bottom
        st.session_state.selected_model_label = label
        st.session_state.selected_model = MODEL_OPTIONS[label]
        # Cross-sync the sidebar selector's key
        st.session_state.model_selector_sidebar_widget = label
    
    # Model Selection
    st.subheader("🤖 Model Version")
    
    # Show active key status
    key_status_icon = "🔑" if st.session_state.custom_api_key else "🌐"
    key_status_label = "Personal Key Active" if st.session_state.custom_api_key else "Shared Key Active"
    st.caption(f"{key_status_icon} **{key_status_label}**")
    
    if "selected_model_label" not in st.session_state:
        st.session_state.selected_model_label = list(MODEL_OPTIONS.keys())[0]
        st.session_state.model_selector_bottom = st.session_state.selected_model_label
        st.session_state.model_selector_sidebar_widget = st.session_state.selected_model_label

    selected_model_sidebar = st.selectbox(
        "Choose Gemini Version:",
        options=list(MODEL_OPTIONS.keys()),
        index=list(MODEL_OPTIONS.keys()).index(st.session_state.selected_model_label),
        key="model_selector_sidebar_widget",
        on_change=sync_sidebar
    )
    st.session_state.selected_model = MODEL_OPTIONS[st.session_state.selected_model_label]
    
    st.divider()

    if st.session_state.search_mode == "drive":
        st.subheader("📁 Drive Configuration")
        
        # Guide for finding Folder ID
        with st.expander("💡 How to find a Folder ID?"):
            st.write("1. Open the folder in Google Drive.")
            st.write("2. Look at the browser URL.")
            st.write("3. Copy the ID after 'folders/':")
            st.code("1ABC_xYz123...", language=None)
            st.write("4. Paste it below.")

        @st.cache_data(ttl=600)
        def fetch_folders():
            try:
                # Direct call to drive service
                folders = drive_service.list_folders()
                if isinstance(folders, list):
                    return folders
                return []
            except Exception as e:
                print(f"Error fetching folders: {e}")
                return []

        folders = fetch_folders()
        
        if folders:
            folder_options = {f["name"]: f["id"] for f in folders}
            selected_folder_name = st.selectbox(
                "Select a shared folder:",
                options=list(folder_options.keys()),
                index=0 if "selected_folder_id" not in st.session_state else list(folder_options.values()).index(st.session_state.selected_folder_id) if st.session_state.selected_folder_id in folder_options.values() else 0
            )
            st.session_state.selected_folder_id = folder_options[selected_folder_name]
            st.success(f"Connected to: **{selected_folder_name}**")
            
            if st.button("🔄 Refresh List"):
                st.cache_data.clear()
                st.rerun()
        
        st.divider()
        st.subheader("Manual Folder Entry")
        
        with st.form("manual_folder_form"):
            input_type = st.radio("Add by:", ["Folder ID", "Folder Name"], horizontal=True)
            user_input = st.text_input("Enter ID or Name:", placeholder="Paste here and press 'Apply'")
            submitted = st.form_submit_button("✅ Apply Selection")
            
            if submitted:
                if input_type == "Folder ID":
                    st.session_state.selected_folder_id = user_input
                    st.success(f"ID Applied: {user_input[:10]}...")
                else:
                    with st.spinner("Searching for folder..."):
                        try:
                            # Direct agent call for folder search
                            prompt = f"Find the folder ID for a folder named '{user_input}' and tell me its ID."
                            resp_text, _ = chat_with_agent(
                                prompt, 
                                history=[], 
                                model_name=st.session_state.get("selected_model"),
                                api_key=st.session_state.get("custom_api_key")
                            )
                            st.info(resp_text)
                        except Exception as e:
                            st.error(f"Search failed: {e}")

    else:
        st.subheader("System Configuration")
        local_path = st.text_input("Local System Path:", placeholder="e.g. C:/Users/Documents")
        if local_path:
            if os.path.exists(local_path):
                st.session_state.selected_local_path = local_path
                st.success(f"💻 Connected to System: {os.path.basename(local_path)}")
            else:
                st.error("❌ Path does not exist.")
                st.session_state.selected_local_path = None
        else:
            st.info("Please enter a valid local path to search.")
            st.session_state.selected_local_path = None
    
    st.divider()
    
    with st.expander("🔑 Advanced: Custom API Key"):
        st.info("If you hit quota limits, paste your own Google API key below to continue.")
        custom_key = st.text_input("Google API Key", type="password", value=st.session_state.custom_api_key, help="Get one from aistudio.google.com")
        if custom_key:
            custom_key = custom_key.strip()
        if custom_key != st.session_state.custom_api_key:
            st.session_state.custom_api_key = custom_key
            st.success("Custom Key Applied!")
            
    st.divider()
    st.info("How to use:\n1. Choose your search source\n2. Configure the folder/path\n3. Start chatting!")
    
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Display Chat Messages
for msg in st.session_state.messages:
    content = msg["content"]
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-bubble user-bubble">{content}</div>', unsafe_allow_html=True)
    else:
        # Detect if this was an error message
        low_content = content.lower()
        if "quota limit reached" in low_content:
            display_premium_error("Quota Notice", content, "⏳", "warning")
        elif "model unavailable" in low_content:
            display_premium_error("Model Switch", content, "🤖", "warning")
        elif "connection lost" in low_content or "something went wrong" in low_content:
            display_premium_error("System Notice", content, "ℹ️", "critical")
        else:
            st.markdown(f'<div class="chat-bubble ai-bubble">{content}</div>', unsafe_allow_html=True)

# Model Version Selector (Near Search Bar)
m_cols = st.columns([0.8, 0.2])
with m_cols[1]:
    st.selectbox(
        "LLM",
        options=list(MODEL_OPTIONS.keys()),
        index=list(MODEL_OPTIONS.keys()).index(st.session_state.selected_model_label),
        key="model_selector_bottom",
        label_visibility="collapsed",
        on_change=sync_bottom
    )

# Chat Input
if prompt := st.chat_input("Search your Drive..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f'<div class="chat-bubble user-bubble">{prompt}</div>', unsafe_allow_html=True)

    # Call Backend Logic Directly
    spinner_text = "Searching Drive..." if st.session_state.get("search_mode") == "drive" else "Searching Local System..."
    with st.spinner(spinner_text):
        try:
            # Set drive/local context
            if st.session_state.get("search_mode") == "drive":
                drive_service.folder_id = st.session_state.get("selected_folder_id")
                mode_context = f"Mode: Drive Search. Folder: {st.session_state.get('selected_folder_id', 'Root')}"
            else:
                local_service.root_path = st.session_state.get("selected_local_path")
                mode_context = f"Mode: Local Search. Path: {st.session_state.get('selected_local_path')}"

            # Prepare history for backend
            history = []
            for m in st.session_state.messages[:-1]:
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))

            # Direct call to agent logic
            full_message = f"{mode_context}\n\nUser Message: {prompt}"
            ai_response, updated_history = chat_with_agent(
                full_message, 
                history, 
                model_name=st.session_state.get("selected_model"),
                api_key=st.session_state.get("custom_api_key")
            )
            
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            
            # Check if it's a "Limit Reached" or "Unavailable" message from our cleaned backend
            if "quota limit reached" in ai_response.lower():
                display_premium_error("Quota Exceeded", ai_response, "⏳", "warning")
            elif "model unavailable" in ai_response.lower():
                display_premium_error("Model Switch Required", ai_response, "🤖", "warning")
            else:
                st.markdown(f'<div class="chat-bubble ai-bubble">{ai_response}</div>', unsafe_allow_html=True)
                
        except Exception as e:
            display_premium_error("System Notice", f"An issue occurred: {str(e)}", "ℹ️", "critical")
