import subprocess
import time
import sys

def run():
    print("Starting Tailor Talk AI Agent...")
    
    # Start Backend
    backend_process = subprocess.Popen([sys.executable, "-m", "backend.main"])
    print("Backend starting on http://localhost:8000")
    
    # Wait for backend to warm up
    time.sleep(2)
    
    # Start Frontend
    print("Frontend starting...")
    frontend_process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "frontend/app.py"])
    
    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    run()
