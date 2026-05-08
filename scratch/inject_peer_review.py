import sys
from pathlib import Path

cli_path = Path(r"c:\Users\user\Documents\GitHub\RuWritingStyles\src\ruwritingstyles\cli.py")

content = cli_path.read_text(encoding="utf-8")

# 1. Add cmd_peer_review handler
handler = """
def cmd_peer_review(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    provider = provider_from_name(args.provider)
    
    print(f"Running Philological Peer Review for: {run_dir.name}...")
    print(f"Reviewer Archetype: {args.archetype}")
    
    try:
        result = run_peer_review(
            repo_root=repo_root,
            run_dir=run_dir,
            provider=provider,
            model=args.model,
            reviewer_archetype_id=args.archetype,
        )
        
        print(f"\nPeer Review Summary (Score: {result['overall_score']}/10)")
        print(f"Recommendation: {result['recommendation'].upper()}")
        print("\nComments:")
        for comment in result['comments']:
            print(f"- [{comment['type']}] {comment['text']}")
            
        # Trigger report refresh
        _write_reports(repo_root, run_dir)
        return 0
    except Exception as e:
        print(f"error: peer review failed: {e}")
        return 1
"""

if "def cmd_peer_review" not in content:
    content = content.replace("from .sentiment import analyze_philological_sentiment", "from .sentiment import analyze_philological_sentiment\nfrom .peer_review import run_peer_review")
    content = content.replace("def cmd_migrate(", handler + "\n\ndef cmd_migrate(")

# 2. Add subparser registration
registration = """    peer_review = subparsers.add_parser(
        "peer-review",
        help="Use a second Council archetype to critique the revision and council decisions.",
    )
    peer_review.add_argument("run_dir", type=Path, help="The run directory to review.")
    peer_review.add_argument("--archetype", required=True, help="Archetype ID to act as reviewer.")
    _add_provider_args(peer_review)
    peer_review.set_defaults(func=cmd_peer_review)
"""

if '"peer-review"' not in content:
    content = content.replace('    migrate = subparsers.add_parser(', registration + "\n    migrate = subparsers.add_parser(")

cli_path.write_text(content, encoding="utf-8")
print("CLI updated with peer-review command successfully.")
