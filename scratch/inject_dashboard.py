import sys
from pathlib import Path

cli_path = Path(r"c:\Users\user\Documents\GitHub\RuWritingStyles\src\ruwritingstyles\cli.py")

content = cli_path.read_text(encoding="utf-8")

# 1. Add cmd_dashboard handler
handler = """
def cmd_dashboard(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    print("Generating Interactive Project Dashboard...")
    try:
        from .dashboard import generate_project_dashboard
        output_path = args.output if args.output else repo_root / "DASHBOARD.html"
        path = generate_project_dashboard(repo_root, output_path)
        print(f"Success! Dashboard saved to: {path.relative_to(repo_root)}")
        return 0
    except Exception as e:
        print(f"error: dashboard generation failed: {e}")
        return 1
"""

if "def cmd_dashboard" not in content:
    content = content.replace("from .peer_review import run_peer_review", "from .peer_review import run_peer_review\nfrom .dashboard import generate_project_dashboard")
    content = content.replace("def cmd_migrate(", handler + "\n\ndef cmd_migrate(")

# 2. Add subparser registration
registration = """    dashboard = subparsers.add_parser(
        "dashboard",
        help="Generate a project-wide interactive HTML dashboard of all runs and metrics.",
    )
    dashboard.add_argument("--output", "-o", type=Path, help="Output HTML path.")
    dashboard.set_defaults(func=cmd_dashboard)
"""

if '"dashboard"' not in content:
    content = content.replace('    migrate = subparsers.add_parser(', registration + "\n    migrate = subparsers.add_parser(")

cli_path.write_text(content, encoding="utf-8")
print("CLI updated with dashboard command successfully.")
