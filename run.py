import subprocess
import sys

def run():
    print("🚀 Launching Tailor Talk AI Agent...")
    # Just run Streamlit. The backend logic is now imported directly in app.py.
    subprocess.run([sys.executable, "-m", "streamlit", "run", "frontend/app.py"])

if __name__ == "__main__":
    run()
