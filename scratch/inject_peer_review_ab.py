import sys
from pathlib import Path

cli_path = Path(r"c:\Users\user\Documents\GitHub\RuWritingStyles\src\ruwritingstyles\cli.py")

content = cli_path.read_text(encoding="utf-8")

# 1. Add cmd_peer_review_ab handler
handler = """
def cmd_peer_review_ab(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    provider = provider_from_name(args.provider)
    archetypes = args.archetypes
    
    print(f"Running Peer Review A/B Test for: {run_dir.name}...")
    print(f"Comparing Archetypes: {', '.join(archetypes)}")
    
    results = []
    for arch_id in archetypes:
        print(f"  -> Reviewing as: {arch_id}")
        try:
            res = run_peer_review(
                repo_root=repo_root,
                run_dir=run_dir,
                provider=provider,
                model=args.model,
                reviewer_archetype_id=arch_id,
            )
            # Rename the file to avoid overwrite
            p = run_dir / "peer-review.json"
            new_p = run_dir / f"peer-review-{arch_id.replace(' ', '-').lower()}.json"
            if p.exists():
                new_p.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            
            results.append(res)
        except Exception as e:
            print(f"    error for {arch_id}: {e}")
            
    if results:
        report_path = _write_peer_review_ab_report(repo_root, run_dir, results)
        print(f"\nPeer Review A/B Test Complete! Report: {report_path.relative_to(repo_root)}")
        return 0
    return 1


def _write_peer_review_ab_report(repo_root: Path, run_dir: Path, results: list[dict[str, Any]]) -> Path:
    html = [
        "<html><head><title>Peer Review A/B Comparison</title>",
        "<style>",
        "  body { font-family: system-ui; padding: 2rem; }",
        "  table { width: 100%; border-collapse: collapse; }",
        "  th, td { border: 1px solid #ddd; padding: 1rem; text-align: left; vertical-align: top; }",
        "  th { background: #f4f4f4; }",
        "  .recommendation { font-weight: bold; }",
        "  .ACCEPT { color: green; }",
        "  .MAJOR_REVISION { color: red; }",
        "</style></head><body>",
        f"<h1>Peer Review A/B Comparison: {run_dir.name}</h1>",
        "<table><tr>"
    ]
    
    for res in results:
        html.append(f"<th>{res['reviewer_archetype']}</th>")
    html.append("</tr><tr>")
    
    for res in results:
        html.append(f"<td>")
        html.append(f"<div class='recommendation {res['recommendation']}'>Recommendation: {res['recommendation'].upper()}</div>")
        html.append(f"<div>Score: {res['overall_score']}/10</div>")
        html.append("<ul>")
        for c in res.get('comments', []):
            html.append(f"<li><b>{c['type']}</b>: {c['text']}</li>")
        html.append("</ul></td>")
        
    html.append("</tr></table></body></html>")
    
    report_path = run_dir / "peer-review-ab.html"
    report_path.write_text("\\n".join(html), encoding="utf-8")
    return report_path
"""

if "def cmd_peer_review_ab" not in content:
    content = content.replace("def cmd_migrate(", handler + "\n\ndef cmd_migrate(")

# 2. Add subparser registration
registration = """    peer_review_ab = subparsers.add_parser(
        "peer-review-ab",
        help="Compare multiple peer reviewers (archetypes) on the same revision.",
    )
    peer_review_ab.add_argument("run_dir", type=Path, help="The run directory to review.")
    peer_review_ab.add_argument("--archetypes", nargs="+", required=True, help="List of archetype IDs.")
    _add_provider_args(peer_review_ab)
    peer_review_ab.set_defaults(func=cmd_peer_review_ab)
"""

if '"peer-review-ab"' not in content:
    content = content.replace('    migrate = subparsers.add_parser(', registration + "\n    migrate = subparsers.add_parser(")

cli_path.write_text(content, encoding="utf-8")
print("CLI updated with peer-review-ab successfully.")
