import sys
from pathlib import Path

cli_path = Path(r"c:\Users\user\Documents\GitHub\RuWritingStyles\src\ruwritingstyles\cli.py")

content = cli_path.read_text(encoding="utf-8")

# 1. Add cmd_web handler
handler = """
def cmd_web(args: argparse.Namespace) -> int:
    import subprocess
    import time
    import webbrowser
    
    repo_root = repo_root_from()
    print("Launching RuWritingStyles Web Studio...")
    
    # 1. Start API Backend
    api_process = subprocess.Popen(
        ["python", "-m", "ruwritingstyles.api"],
        cwd=repo_root
    )
    
    # 2. Start Vite Frontend (if in dev mode)
    web_dir = repo_root / "web"
    if web_dir.exists():
        print("Starting Vite development server...")
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=web_dir
        )
        time.sleep(2)
        webbrowser.open("http://localhost:5173")
    else:
        print("Frontend directory not found. Please run 'npm install' in 'web/'.")
        return 1
        
    try:
        api_process.wait()
    except KeyboardInterrupt:
        print("\\nShutting down...")
        api_process.terminate()
        if frontend_process:
            frontend_process.terminate()
            
    return 0
"""

if "def cmd_web" not in content:
    content = content.replace("from .dashboard import generate_project_dashboard", "from .dashboard import generate_project_dashboard\nfrom .api import app as web_app")
    content = content.replace("def cmd_migrate(", handler + "\n\ndef cmd_migrate(")

# 2. Add subparser registration
registration = """    web = subparsers.add_parser(
        "web",
        help="Launch the modern web frontend (RuWritingStyles Web Studio).",
    )
    web.set_defaults(func=cmd_web)
"""

if '"web"' not in content:
    content = content.replace('    migrate = subparsers.add_parser(', registration + "\n    migrate = subparsers.add_parser(")

cli_path.write_text(content, encoding="utf-8")
print("CLI updated with web command successfully.")
