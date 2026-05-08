import sys
from pathlib import Path

cli_path = Path(r"c:\Users\user\Documents\GitHub\RuWritingStyles\src\ruwritingstyles\cli.py")
handler_path = Path(r"c:\Users\user\Documents\GitHub\RuWritingStyles\scratch\benchmark_handler.py")

content = cli_path.read_text(encoding="utf-8")
handler = handler_path.read_text(encoding="utf-8")

# 1. Insert handler before main
if "def cmd_eval_benchmark" not in content:
    content = content.replace("def main(", handler + "\n\ndef main(")

# 2. Insert subparser registration
registration = """    eval_benchmark = subparsers.add_parser(
        "eval-benchmark",
        help="Run the evaluation suite on multiple models and generate a leaderboard.",
    )
    eval_benchmark.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="List of model names to benchmark (e.g. 'gpt-5.5' 'gemini-3.1-pro-preview').",
    )
    eval_benchmark.add_argument(
        "--provider",
        choices=["openai", "google", "anthropic"],
        required=True,
        help="Provider to use for all models in this benchmark.",
    )
    eval_benchmark.set_defaults(func=cmd_eval_benchmark)
"""

if '"eval-benchmark"' not in content:
    content = content.replace('    eval_promote = subparsers.add_parser(', registration + "\n    eval_promote = subparsers.add_parser(")

cli_path.write_text(content, encoding="utf-8")
print("CLI updated successfully via python script.")
