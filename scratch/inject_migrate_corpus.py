import sys
from pathlib import Path

cli_path = Path(r"c:\Users\user\Documents\GitHub\RuWritingStyles\src\ruwritingstyles\cli.py")

content = cli_path.read_text(encoding="utf-8")

# 1. Add cmd_migrate_corpus handler
handler = """
def cmd_migrate_corpus(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    input_dir = args.input_dir if args.input_dir.is_absolute() else (Path.cwd() / args.input_dir)
    provider = provider_from_name(args.provider)
    
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"error: {input_dir} is not a directory")
        return 1
        
    md_files = sorted(input_dir.glob("*.md"))
    if not md_files:
        print(f"no .md files found in {input_dir}")
        return 0
        
    output_dir = input_dir / "migrated"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Migrating corpus ({len(md_files)} files) to style: {args.to_style}...")
    
    success_count = 0
    for md_file in md_files:
        print(f"  -> {md_file.name}")
        try:
            migrated_path = migrate_document_style(
                repo_root=repo_root,
                input_file=md_file,
                from_style_id=args.from_style,
                to_style_id=args.to_style,
                provider=provider,
                model=args.model,
            )
            # Copy to corpus output dir with original name
            target = output_dir / md_file.name
            target.write_text(migrated_path.read_text(encoding="utf-8"), encoding="utf-8")
            success_count += 1
        except Exception as e:
            print(f"    error: {e}")
            
    print(f"\nMigration Complete! {success_count}/{len(md_files)} files saved to {output_dir.relative_to(repo_root)}")
    return 0 if success_count == len(md_files) else 1
"""

if "def cmd_migrate_corpus" not in content:
    content = content.replace("def cmd_migrate(", handler + "\n\ndef cmd_migrate(")

# 2. Add subparser registration
registration = """    migrate_corpus = subparsers.add_parser(
        "migrate-corpus",
        help="Migrate an entire directory of documents to a new philological style.",
    )
    migrate_corpus.add_argument("input_dir", type=Path, help="Directory containing .md files.")
    migrate_corpus.add_argument("--from-style", help="The original style (optional context).")
    migrate_corpus.add_argument("--to-style", required=True, help="The target style ID.")
    _add_provider_args(migrate_corpus)
    migrate_corpus.set_defaults(func=cmd_migrate_corpus)
"""

if '"migrate-corpus"' not in content:
    content = content.replace('    migrate = subparsers.add_parser(', registration + "\n    migrate = subparsers.add_parser(")

cli_path.write_text(content, encoding="utf-8")
print("CLI updated with migrate-corpus successfully.")
