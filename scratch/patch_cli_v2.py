import sys
from pathlib import Path
import re

path = Path('src/ruwritingstyles/cli.py')
content = path.read_text(encoding='utf-8')

# Rewrite the syntax block to be very simple
new_syntax_block = """
            # Phase F: Syntax Assessment
            from .syntax import create_syntax_bundle
            from .execution import execute_syntax_artifact
            syntax_bundle = create_syntax_bundle(repo_root=repo_root, run_dir=run_dir)
            if syntax_bundle:
                s_path = Path(syntax_bundle["syntax_path"])
                print(f"created {s_path.relative_to(repo_root)}")
                execute_syntax_artifact(
                    repo_root=repo_root,
                    syntax_path=s_path,
                    provider=provider_from_name(args.provider),
                    model=(args.model or model_policy.resolve_model("verification", args.provider))
                )
                print(f"completed {s_path.relative_to(repo_root)}")
"""

# Find the spot after impact assessment and before the end of the loop/report
# We'll use the previous patch as a marker or find the impact block again
pattern = re.compile(r"execute_impact_artifact\(.*?\)\n\s+print\(f\"completed {impact.impact_json.relative_to\(repo_root\)}\"\)", re.DOTALL)
if pattern.search(content):
    content = pattern.sub(lambda m: m.group(0) + new_syntax_block, content)
    print("Injected simplified syntax block")
else:
    print("Could not find impact block for injection")

path.write_text(content, encoding='utf-8')
