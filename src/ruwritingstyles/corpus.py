"""Corpus Management and Deep Retrieval (Phase VI)."""

import logging
import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CorpusManager:
    """
    Manages the primary philological literature corpus.
    Uses SQLite FTS5 for efficient full-text search and quote extraction.
    """
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.db_path = repo_root / "rws.db"
        # Corpus texts live in the private sibling repo RuWritingStyles-corpus
        # (copyrighted sources are not distributed with this public repo).
        # Resolution order: RWS_CORPUS_DIR env var, local PDFtoTXT/, sibling repo.
        corpus_env = os.environ.get("RWS_CORPUS_DIR")
        if corpus_env:
            self.corpus_dir = Path(corpus_env)
        elif (repo_root / "PDFtoTXT").exists():
            self.corpus_dir = repo_root / "PDFtoTXT"
        else:
            self.corpus_dir = repo_root.parent / "RuWritingStyles-corpus" / "PDFtoTXT"

    def ingest_all(self, force: bool = False):
        """Index all TXT files in the corpus directory."""
        if not self.corpus_dir.exists():
            logger.warning(f"Corpus directory not found: {self.corpus_dir}")
            return

        txt_files = list(self.corpus_dir.glob("*.txt"))
        logger.info(f"CorpusManager: Found {len(txt_files)} TXT files for ingestion.")

        for txt_file in txt_files:
            self.ingest_file(txt_file, force=force)

    def ingest_file(self, file_path: Path, force: bool = False):
        """Index a single TXT file into FTS5."""
        try:
            rel_path = str(file_path.relative_to(self.repo_root))
        except ValueError:
            # Corpus file lives outside the repo (private sibling repo);
            # keep the index key in the historical PDFtoTXT/<name> form.
            rel_path = str(Path("PDFtoTXT") / file_path.name)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Check if already indexed
            if not force:
                row = conn.execute("SELECT file_path FROM corpus_metadata WHERE file_path = ?", (rel_path,)).fetchone()
                if row:
                    logger.debug(f"Skipping already indexed file: {rel_path}")
                    return

            logger.info(f"Ingesting corpus file: {rel_path}")
            content = file_path.read_text(encoding="utf-8", errors="replace")
            
            # Simple chunking by paragraph (double newline)
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            
            # Metadata extraction (heuristic)
            name_parts = file_path.stem.split("_")
            year = 0
            author = "Unknown"
            title = file_path.stem
            
            if name_parts[0].isdigit() and len(name_parts[0]) == 4:
                year = int(name_parts[0])
                author = name_parts[1] if len(name_parts) > 1 else "Unknown"
            elif len(name_parts) > 1:
                author = name_parts[0]
            
            # Transactional Insert
            conn.execute("DELETE FROM corpus_segments WHERE file_path = ?", (rel_path,))
            conn.execute("INSERT OR REPLACE INTO corpus_metadata (file_path, title, author, year) VALUES (?, ?, ?, ?)",
                         (rel_path, title, author, year))
            
            for i, p in enumerate(paragraphs):
                conn.execute("INSERT INTO corpus_segments (file_path, segment_index, content) VALUES (?, ?, ?)",
                             (rel_path, i, p))
            
            conn.commit()

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the corpus using FTS5."""
        # Sanitize query for FTS5 (basic)
        sanitized_query = query.replace('"', '""')
        
        results = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Use snippet() for context
            sql = """
                SELECT 
                    s.file_path, 
                    s.segment_index, 
                    snippet(corpus_segments, 2, '«', '»', '...', 20) as snippet,
                    s.content as full_content,
                    m.title,
                    m.author,
                    m.year
                FROM corpus_segments s
                JOIN corpus_metadata m ON s.file_path = m.file_path
                WHERE corpus_segments MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            try:
                rows = conn.execute(sql, (sanitized_query, limit)).fetchall()
                for row in rows:
                    results.append({
                        "file": row["file_path"],
                        "title": row["title"],
                        "author": row["author"],
                        "year": row["year"],
                        "snippet": row["snippet"],
                        "text": row["full_content"]
                    })
            except sqlite3.OperationalError as e:
                logger.error(f"FTS5 Search failed: {e}")
                
        return results
