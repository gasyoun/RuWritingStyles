from .citations import extract_citations

BIB_DATABASE = {
    "zaliznyak": """@book{zaliznyak2004,
  author = {Зализняк, А. А.},
  title = {«Слово о полку Игореве»: взгляд лингвиста},
  year = {2004},
  publisher = {Языки славянской культуры},
  address = {Москва}
}""",
    "tronsky": """@book{tronsky1960,
  author = {Тронский, И. М.},
  title = {Историческая грамматика латинского языка},
  year = {1960},
  publisher = {Издательство Ленинградского университета},
  address = {Ленинград}
}""",
    "gasparov": """@book{gasparov1984,
  author = {Гаспаров, М. Л.},
  title = {Очерк истории русского стиха: Метрика, ритмика, рифма, строфика},
  year = {1984},
  publisher = {Наука},
  address = {Москва}
}"""
}

def generate_bibtex(run_id: str, revised_text: str = "") -> str:
    """Generate BibTeX entries for the citations found in the text."""
    
    citations = extract_citations(revised_text)
    entries = []
    
    # Simple mapping: if citation contains keyword, include the entry
    for key, bib in BIB_DATABASE.items():
        if not revised_text: # Default to all if no text provided (backwards compatibility)
            entries.append(bib)
            continue
            
        for cite in citations:
            if key.lower() in cite.lower():
                entries.append(bib)
                break
                
    header = f"% BibTeX for RuWritingStyles Run: {run_id}\n"
    if citations:
        header += f"% Extracted Citations: {', '.join(citations)}\n"
    header += "\n"
    
    return header + "\n\n".join(entries)

def write_bibtex(run_dir: Path):
    run_id = run_dir.name
    revised_path = run_dir / "revised.md"
    revised_text = revised_path.read_text(encoding="utf-8") if revised_path.exists() else ""
    
    bib_content = generate_bibtex(run_id, revised_text)
    (run_dir / "references.bib").write_text(bib_content, encoding="utf-8")
