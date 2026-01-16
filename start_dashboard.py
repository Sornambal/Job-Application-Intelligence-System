#!/usr/bin/env python3
"""
Dashboard Startup Script
Ensures required packages are installed in the project's virtual environment
and starts the web dashboard on http://localhost:5000
"""

import subprocess
import sys
import os
import webbrowser
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_preferred_python():
    """Prefer the project's venv Python; fallback to current interpreter."""
    venv_py_win = os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe")
    venv_py_nix = os.path.join(ROOT_DIR, ".venv", "bin", "python")
    if os.path.exists(venv_py_win):
        print(f"🧰 Using venv Python: {venv_py_win}")
        return venv_py_win
    if os.path.exists(venv_py_nix):
        print(f"🧰 Using venv Python: {venv_py_nix}")
        return venv_py_nix
    print("⚠️  .venv not found — using system Python. Consider creating a venv for reliability.")
    return sys.executable

def ensure_packages(python_exec, packages):
    """Install required packages using the specified Python interpreter."""
    print("📦 Ensuring required packages are installed:", ", ".join(packages))
    try:
        subprocess.check_call([python_exec, "-m", "pip", "install", *packages])
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError as e:
        print("❌ Failed to install dependencies:", e)
        print("   Try running: pip install " + " ".join(packages))
        raise

def start_dashboard(python_exec):
    """Start the Flask dashboard server using the specified Python interpreter"""
    print("\n" + "="*80)
    print("🚀 Starting Job Application Intelligence Dashboard")
    print("="*80)
    print("\n📊 Dashboard will be available at: http://localhost:5000")
    print("\n📋 Features:")
    print("   • Dashboard with statistics and charts")
    print("   • View all applied jobs (Sheet 1)")
    print("   • View job suggestions (Sheet 2)")
    print("   • Jobs needing attention")
    print("   • Analytics and insights")
    print("\n💡 Tips:")
    print("   • The dashboard auto-refreshes every 30 seconds")
    print("   • Click tabs to view different sections")
    print("   • Use refresh buttons to manually reload data")
    print("\n" + "="*80 + "\n")
    
    # Open browser after a short delay
    time.sleep(2)
    try:
        webbrowser.open('http://localhost:5000')
    except:
        print("⚠️  Could not open browser automatically")
        print("   Please open http://localhost:5000 in your browser")
    
    # Start Flask app
    print("Starting Flask server...\n")
    subprocess.run([python_exec, "app.py"])

if __name__ == "__main__":
    python_exec = get_preferred_python()
    ensure_packages(python_exec, [
        "flask",
        "flask-cors",
        "pandas",
        "openpyxl",
    ])
    start_dashboard(python_exec)
