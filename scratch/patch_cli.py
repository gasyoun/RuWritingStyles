import sys
from pathlib import Path

path = Path('src/ruwritingstyles/cli.py')
content = path.read_text(encoding='utf-8')

# 1. Add archetype argument to run subparser
old_run = '    _add_execute_args(run)\n    run.set_defaults(func=cmd_run)'
new_run = '    run.add_argument("--archetype", help="Council archetype ID")\n    _add_execute_args(run)\n    run.set_defaults(func=cmd_run)'
if old_run in content:
    content = content.replace(old_run, new_run)
    print("Updated subparser")
else:
    print("Could not find subparser block")

# 2. Add archetype_id to council bundle creation
old_council = '            verification_feedback=verification_feedback,\n        )'
new_council = '            verification_feedback=verification_feedback,\n            archetype_id=getattr(args, "archetype", None),\n        )'
if old_council in content:
    content = content.replace(old_council, new_council)
    print("Updated council bundle")
else:
    print("Could not find council bundle block")

# 3. Add syntax assessment step to cmd_run
# We'll insert it after impact assessment
old_impact = '            print(f"completed {impact.impact_json.relative_to(repo_root)}")'
new_impact = old_impact + '\n\n            # Phase F: Syntax Assessment\n            from .syntax import create_syntax_bundle\n            from .execution import execute_syntax_artifact\n            syntax_bundle = create_syntax_bundle(repo_root=repo_root, run_dir=run_dir)\n            print(f"created {Path(syntax_bundle[\'syntax_path\']).relative_to(repo_root)}")\n            execute_syntax_artifact(\n                repo_root=repo_root,\n                syntax_path=Path(syntax_bundle["syntax_path"]),\n                provider=provider_from_name(args.provider),\n                model=args.model or model_policy.resolve_model("verification", args.provider),\n            )\n            print(f"completed {Path(syntax_bundle[\'syntax_path\']).relative_to(repo_root)}")'

if old_impact in content:
    content = content.replace(old_impact, new_impact)
    print("Updated syntax step")
else:
    print("Could not find impact block")

path.write_text(content, encoding='utf-8')
