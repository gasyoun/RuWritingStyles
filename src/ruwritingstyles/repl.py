"""Interactive multi-agent REPL for style deliberation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .providers import BaseProvider
from .config import Manifest, load_archetypes


def run_council_repl(
    *,
    repo_root: Path,
    run_dir: Path,
    manifest: Manifest,
    provider: BaseProvider,
    model: str | None,
):
    """Run an interactive REPL with the Council."""
    
    council_path = run_dir / "council.json"
    if not council_path.exists():
        print(f"error: council.json not found in {run_dir}. Run `rws council` first.")
        return

    # Load context
    reviews_dir = run_dir / "reviews"
    review_summaries = []
    for p in sorted(reviews_dir.glob("*.review.json")):
        review = json.loads(p.read_text(encoding="utf-8"))
        style_id = review.get("style_id", p.name)
        findings = review.get("findings", [])
        review_summaries.append(f"Style: {style_id} ({len(findings)} findings)")

    # Resolve Archetype
    archetypes = load_archetypes(repo_root)
    archetype_map = {a.id: a for a in archetypes}
    archetype = archetype_map.get(manifest.council.archetype) if manifest.council else None
    
    persona = archetype.name if archetype else "The Coordinator"
    
    print(f"\n--- RuWritingStyles Council REPL ---")
    print(f"Council Persona: {persona}")
    print(f"Context: {len(review_summaries)} style reviews loaded.")
    print("Type your instructions or questions. Use '/exit' to quit, '/save' to update council.json.\n")

    history = [
        {"role": "system", "content": f"You are the RuWritingStyles Council ({persona}). You are in a real-time deliberation session with a Human Editor. Discuss the stylistic choices, justify your decisions, and be ready to change them based on feedback. Your goals: {archetype.instructions if archetype else 'Balanced synthesis.'}"}
    ]

    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input:
                continue
            
            if user_input.lower() == "/exit":
                break
            
            if user_input.lower() == "/save":
                # In a real implementation, we would ask the LLM to output a new council-result.json
                print("Note: /save would now trigger a re-synthesis of the council-result.json based on this chat.")
                continue

            history.append({"role": "user", "content": user_input})
            
            # Simple chat completion
            # We don't have a multi-turn 'chat' method in BaseProvider yet, so we'll simulate with prompt
            full_prompt = ""
            for msg in history:
                full_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
            full_prompt += f"{persona.upper()}:"

            response = provider.generate(
                prompt=full_prompt,
                model=model,
                system_instructions=f"You are the {persona} archetype.",
            )
            
            print(f"\n{persona} > {response}\n")
            history.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"error: {e}")
            break

    print("\nREPL session ended.")
