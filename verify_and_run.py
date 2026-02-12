"""
Quick Flask verification and setup script.
Run this to verify Flask installation and start the server.
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.9+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ required")
        print(f"   You have Python {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor} found")
    return True

def check_flask_installed():
    """Check if Flask is installed"""
    try:
        import flask
        print(f"✅ Flask {flask.__version__} installed")
        return True
    except ImportError:
        print("❌ Flask not found")
        return False

def install_flask():
    """Install Flask if not found"""
    print("\nInstalling Flask and dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def start_server():
    """Start the Flask server"""
    print("\n" + "="*70)
    print("Starting Flask Web Server...")
    print("="*70)
    print("\nOpen your browser and go to:")
    print("➜ http://localhost:5000")
    print("\nPress CTRL+C to stop the server")
    print("="*70 + "\n")
    
    try:
        from app import app
        app.run(debug=True, port=5000)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False
    return True

def main():
    """Main verification and startup flow"""
    print("\n" + "="*70)
    print("Research Agent - Flask Setup Verification")
    print("="*70 + "\n")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check Flask installation
    if not check_flask_installed():
        if not install_flask():
            sys.exit(1)
    
    # All checks passed
    print("\n✅ All checks passed! Starting server...\n")
    
    # Start server
    if not start_server():
        sys.exit(1)

if __name__ == "__main__":
    main()
