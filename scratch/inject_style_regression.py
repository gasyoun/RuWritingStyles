import sys
from pathlib import Path

cli_path = Path(r"c:\Users\user\Documents\GitHub\RuWritingStyles\src\ruwritingstyles\cli.py")

content = cli_path.read_text(encoding="utf-8")

# 1. Add cmd_style_regression handler
handler = """
def cmd_style_regression(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    style_id = args.style
    provider = provider_from_name(args.provider)
    
    print(f"Running Style Regression Test for: {style_id}...")
    
    try:
        from .evals import run_style_regression_test
        result = run_style_regression_test(
            repo_root=repo_root,
            style_id=style_id,
            provider_name=args.provider,
            model=args.model,
            execute=True,
        )
        
        print(f"\nStyle Regression Result: {result['status'].upper()}")
        print(f"Total Anchors: {result['total_anchors']}")
        print(f"Passed:        {result['passed_anchors']}")
        print(f"Regressions:   {len(result['regressions'])}")
        
        if result['regressions']:
            print("\nREGRESSIONS DETECTED:")
            for reg in result['regressions']:
                print(f"- [Case: {reg['case_id']}] {reg['issue']}")
                
        return 0 if not result['regressions'] else 1
    except Exception as e:
        print(f"error: style regression failed: {e}")
        return 1
"""

if "def cmd_style_regression" not in content:
    content = content.replace("def cmd_migrate(", handler + "\n\ndef cmd_migrate(")

# 2. Add subparser registration
registration = """    style_regression = subparsers.add_parser(
        "style-regression",
        help="Verify a style passport against its anchor test cases to detect linguistic drift.",
    )
    style_regression.add_argument("--style", required=True, help="Style ID to test.")
    _add_provider_args(style_regression)
    style_regression.set_defaults(func=cmd_style_regression)
"""

if '"style-regression"' not in content:
    content = content.replace('    migrate = subparsers.add_parser(', registration + "\n    migrate = subparsers.add_parser(")

cli_path.write_text(content, encoding="utf-8")
print("CLI updated with style-regression successfully.")
