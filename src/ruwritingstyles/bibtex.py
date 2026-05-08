"""BibTeX exporter for RuWritingStyles (Phase H)."""

from __future__ import annotations
from pathlib import Path

def generate_bibtex(run_id: str) -> str:
    """Generate BibTeX entries for the corpora used in the project."""
    
    entries = [
        """@book{zaliznyak2004,
  author = {Зализняк, А. А.},
  title = {«Слово о полку Игореве»: взгляд лингвиста},
  year = {2004},
  publisher = {Языки славянской культуры},
  address = {Москва}
}""",
        """@book{tronsky1960,
  author = {Тронский, И. М.},
  title = {Историческая грамматика латинского языка},
  year = {1960},
  publisher = {Издательство Ленинградского университета},
  address = {Ленинград}
}""",
        """@book{gasparov1984,
  author = {Гаспаров, М. Л.},
  title = {Очерк истории русского стиха: Метрика, ритмика, рифма, строфика},
  year = {1984},
  publisher = {Наука},
  address = {Москва}
}"""
    ]
    
    header = f"% BibTeX for RuWritingStyles Run: {run_id}\n\n"
    return header + "\n\n".join(entries)

def write_bibtex(run_dir: Path):
    run_id = run_dir.name
    bib_content = generate_bibtex(run_id)
    (run_dir / "references.bib").write_text(bib_content, encoding="utf-8")
