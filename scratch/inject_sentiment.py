import sys
from pathlib import Path

cli_path = Path(r"c:\Users\user\Documents\GitHub\RuWritingStyles\src\ruwritingstyles\cli.py")

content = cli_path.read_text(encoding="utf-8")

# 1. Add cmd_sentiment handler
handler = """
def cmd_sentiment(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    provider = provider_from_name(args.provider)
    
    print(f"Analyzing philological sentiment for: {run_dir.name}...")
    try:
        result = analyze_philological_sentiment(
            repo_root=repo_root,
            run_dir=run_dir,
            provider=provider,
            model=args.model,
        )
        print(f"\nSentiment Shift Analysis:")
        print(f"- Academic Distance: {result['original']['distance']} -> {result['revised']['distance']} (Delta: {result['deltas']['distance']})")
        print(f"- Certainty:         {result['original']['certainty']} -> {result['revised']['certainty']} (Delta: {result['deltas']['certainty']})")
        print(f"- Complexity:        {result['original']['complexity']} -> {result['revised']['complexity']} (Delta: {result['deltas']['complexity']})")
        print(f"\nJustification: {result['justification']}")
        
        # Trigger report refresh
        _write_reports(repo_root, run_dir)
        return 0
    except Exception as e:
        print(f"error: sentiment analysis failed: {e}")
        return 1
"""

if "def cmd_sentiment" not in content:
    content = content.replace("from .migration import migrate_document_style", "from .migration import migrate_document_style\nfrom .sentiment import analyze_philological_sentiment")
    content = content.replace("def cmd_migrate(", handler + "\n\ndef cmd_migrate(")

# 2. Add subparser registration
registration = """    sentiment = subparsers.add_parser(
        "sentiment",
        help="Analyze the tone, distance, and scholarly register shift of a revision.",
    )
    sentiment.add_argument("run_dir", type=Path, help="The run directory to analyze.")
    _add_provider_args(sentiment)
    sentiment.set_defaults(func=cmd_sentiment)
"""

if '"sentiment"' not in content:
    content = content.replace('    migrate = subparsers.add_parser(', registration + "\n    migrate = subparsers.add_parser(")

cli_path.write_text(content, encoding="utf-8")
print("CLI updated with sentiment command successfully.")
