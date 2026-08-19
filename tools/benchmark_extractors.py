"""Scored bake-off of PDF text extractors on Russian-language galleys (D08/D09).

Runs every available extractor over every sample, scores each result through the
production sanity gate (`ruwritingstyles.extract.sanity`), and prints a Markdown
matrix. The verdict it produces is pinned in `config.PDF_EXTRACTOR_CHAIN`; see
`docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md`.

Samples never enter this repo (D18). They are read from a directory outside it:

    python tools/benchmark_extractors.py --report \
        --samples <scratch>/samples --corpus ../RuWritingStyles-corpus/PDFtoTXT

Uninstalled candidates (D19) are benchmarked from a throwaway virtualenv passed
with `--venv <path>`; anything that is not importable there is reported
`unavailable` rather than silently dropped.

Usage:
    python tools/benchmark_extractors.py --report          # matrix to stdout
    python tools/benchmark_extractors.py --json out.json   # raw scores
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from ruwritingstyles.extract import sanity, verdict_for  # noqa: E402

# The two corpus PDFs `.ai_state.md` records as pdftotext Cyrillic failures.
# Mandatory samples: a comparison that only covers PDFs which already worked
# proves nothing.
CORPUS_SAMPLES = ("Digital_Humanities-2023.pdf", "Digital-Humanities_IgorPilshchikov.pdf")

# Cap OCR candidates: a full 20-page galley through tesseract costs minutes and
# the sanity gate needs only enough text to judge the encoding.
OCR_PAGE_CAP = 6

# Per-document budget. This is a real acceptance criterion, not just a guard: the
# harvester has ~300 articles to get through, so an engine that cannot return text
# for one document inside the budget is unusable for the workload whatever its
# accuracy. Exceeding it is recorded as `timeout` — a measurement, not an error.
# Override with --timeout.
TIMEOUT = 300


class Unavailable(Exception):
    """Candidate cannot run here; recorded as `unavailable`, never retried (D19)."""


def _budget_check(started: float, label: str) -> None:
    """Enforce TIMEOUT on in-process candidates too.

    `subprocess.run(timeout=...)` bounds only the venv and CLI candidates. Without
    this, an in-process engine runs unbounded and gets scored `ok` at 504 s while a
    subprocess engine is cut off at the budget — the matrix would be comparing two
    different rules. Checked between pages, so the cost of overrunning is one page.
    """
    if time.monotonic() - started > TIMEOUT:
        raise subprocess.TimeoutExpired(label, TIMEOUT)


# --------------------------------------------------------------------------- #
# Candidates
# --------------------------------------------------------------------------- #


def _run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, encoding="utf-8", errors="replace",
        timeout=TIMEOUT, **kw
    )


def c_pdftotext(pdf: Path) -> str:
    if not shutil.which("pdftotext"):
        raise Unavailable("pdftotext not on PATH")
    return _run(["pdftotext", str(pdf), "-"]).stdout


def c_pdftotext_layout(pdf: Path) -> str:
    if not shutil.which("pdftotext"):
        raise Unavailable("pdftotext not on PATH")
    return _run(["pdftotext", "-layout", str(pdf), "-"]).stdout


def c_pymupdf_text(pdf: Path) -> str:
    """PyMuPDF plain text — the same call path the `deeppapernote` skill uses."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - environment probe
        raise Unavailable("PyMuPDF not importable") from exc
    with fitz.open(pdf) as doc:
        return "\n".join(page.get_text("text") for page in doc)


def c_pymupdf_blocks(pdf: Path) -> str:
    """PyMuPDF block order — better on the two-column galleys RCSI publishes."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover
        raise Unavailable("PyMuPDF not importable") from exc
    out: list[str] = []
    with fitz.open(pdf) as doc:
        for page in doc:
            blocks = sorted(page.get_text("blocks"), key=lambda b: (round(b[0]), b[1]))
            out.extend(b[4] for b in blocks if len(b) > 4 and isinstance(b[4], str))
    return "\n".join(out)


def c_pdfminer(pdf: Path) -> str:
    try:
        from pdfminer.high_level import extract_text
    except ImportError as exc:  # pragma: no cover
        raise Unavailable("pdfminer.six not importable") from exc
    return extract_text(str(pdf))


def c_pypdf(pdf: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise Unavailable("pypdf not importable") from exc
    return "\n".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages)


def c_ocrmypdf_rus(pdf: Path) -> str:
    """Rasterise + tesseract rus through ocrmypdf, then read the new text layer.

    The text layer is read with PyMuPDF, NOT `pdftotext`. Reading it with poppler
    scored 0.00 Cyrillic on every Russian sample — measuring the poppler bug a
    second time rather than measuring tesseract, which the direct
    `tesseract rus (render)` candidate shows handles this material fine.
    """
    if not shutil.which("ocrmypdf"):
        raise Unavailable("ocrmypdf not on PATH")
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover
        raise Unavailable("PyMuPDF not importable") from exc
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "ocr.pdf"
        proc = _run([
            "ocrmypdf", "--force-ocr", "-l", "rus+eng", "--optimize", "0",
            "--pages", "1-%d" % OCR_PAGE_CAP, str(pdf), str(out),
        ])
        if not out.exists():
            raise Unavailable(
                "ocrmypdf exit %s: %s" % (proc.returncode, proc.stderr.strip()[:120])
            )
        with fitz.open(out) as doc:
            return "\n".join(page.get_text("text") for page in doc)


def c_tesseract_rus(pdf: Path) -> str:
    """Direct render-then-OCR — the crop-then-OCR family, minus ocrmypdf's wrapper."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise Unavailable("PyMuPDF/pytesseract/Pillow not importable") from exc
    if not shutil.which("tesseract"):
        raise Unavailable("tesseract not on PATH")
    started = time.monotonic()
    out: list[str] = []
    with fitz.open(pdf) as doc:
        for page in list(doc)[:OCR_PAGE_CAP]:
            _budget_check(started, "tesseract rus (render)")
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            out.append(pytesseract.image_to_string(img, lang="rus+eng"))
    return "\n".join(out)


def c_easyocr_ru(pdf: Path) -> str:
    """Second OCR engine — a neural recogniser rather than tesseract's line model."""
    try:
        import easyocr
        import fitz
        import numpy as np
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise Unavailable("easyocr/PyMuPDF/Pillow/numpy not importable") from exc
    started = time.monotonic()
    reader = easyocr.Reader(["ru", "en"], gpu=False, verbose=False)
    out: list[str] = []
    with fitz.open(pdf) as doc:
        for page in list(doc)[:OCR_PAGE_CAP]:
            _budget_check(started, "easyocr ru")
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            out.append(" ".join(reader.readtext(np.array(img), detail=0, paragraph=True)))
    return "\n".join(out)


class _VenvCandidate:
    """Run an extractor inside the throwaway venv (D19), reading text off stdout."""

    python: str | None = None

    def __init__(self, label: str, snippet: str) -> None:
        self.label = label
        self.snippet = snippet

    def __call__(self, pdf: Path) -> str:
        python = _VenvCandidate.python
        if python is None or not Path(python).exists():
            raise Unavailable("no --venv given")
        script = Path(tempfile.gettempdir()) / ("bakeoff_%s.py" % self.label)
        script.write_text(
            "import sys\n"
            "sys.stdout.reconfigure(encoding='utf-8')\n"
            "PDF = sys.argv[1]\n" + self.snippet + "\n",
            encoding="utf-8",
        )
        proc = _run([str(python), str(script), str(pdf)])
        if proc.returncode != 0:
            raise Unavailable(
                "%s exit %s: %s" % (self.label, proc.returncode, proc.stderr.strip()[:120])
            )
        return proc.stdout


c_pdfplumber = _VenvCandidate(
    "pdfplumber",
    "import pdfplumber\n"
    "with pdfplumber.open(PDF) as d:\n"
    "    print(chr(10).join((p.extract_text() or '') for p in d.pages))",
)

c_docling = _VenvCandidate(
    "docling",
    "from docling.document_converter import DocumentConverter\n"
    "print(DocumentConverter().convert(PDF).document.export_to_markdown())",
)

c_marker = _VenvCandidate(
    "marker",
    "from marker.converters.pdf import PdfConverter\n"
    "from marker.models import create_model_dict\n"
    "print(PdfConverter(artifact_dict=create_model_dict())(PDF).markdown)",
)

c_unstructured = _VenvCandidate(
    "unstructured",
    "from unstructured.partition.pdf import partition_pdf\n"
    "els = partition_pdf(PDF, languages=['rus', 'eng'])\n"
    "print(chr(10).join(str(e) for e in els))",
)

CANDIDATES: dict[str, Callable[[Path], str]] = {
    "pdftotext": c_pdftotext,
    "pdftotext -layout": c_pdftotext_layout,
    "pymupdf-text": c_pymupdf_text,
    "pymupdf-blocks": c_pymupdf_blocks,
    "pdfminer.six": c_pdfminer,
    "pypdf": c_pypdf,
    "pdfplumber": c_pdfplumber,
    "ocrmypdf+tesseract rus": c_ocrmypdf_rus,
    "tesseract rus (render)": c_tesseract_rus,
    "easyocr ru": c_easyocr_ru,
    "docling": c_docling,
    "marker": c_marker,
    "unstructured": c_unstructured,
}


# --------------------------------------------------------------------------- #
# Harness
# --------------------------------------------------------------------------- #


def collect_samples(
    samples_dir: Path | None, corpus_dir: Path | None
) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    if samples_dir and samples_dir.exists():
        found.extend((p.stem, p) for p in sorted(samples_dir.glob("*.pdf")))
    if corpus_dir and corpus_dir.exists():
        for name in CORPUS_SAMPLES:
            p = corpus_dir / name
            if p.exists():
                found.append(("corpus:" + Path(name).stem, p))
    return found


def score_all(
    samples: list[tuple[str, Path]],
    only: set[str] | None = None,
    latin: set[str] | None = None,
    checkpoint: Callable[[dict[str, Any]], None] | None = None,
    done: dict[str, Any] | None = None,
) -> dict[str, Any]:
    latin = latin or set()
    done = done or {}
    results: dict[str, Any] = {}
    for cname, fn in CANDIDATES.items():
        if only and cname not in only:
            continue
        results[cname] = {}
        for sname, path in samples:
            # Resume: a cell already scored in the merged file is not re-run. The
            # heavy engines take minutes per document, so an interrupted sweep must
            # cost only the cell it was inside, not the whole row.
            if sname in done.get(cname, {}):
                continue
            started = time.monotonic()
            try:
                row: dict[str, Any] = dict(
                    sanity(fn(path), expect_cyrillic=sname not in latin)
                )
                row["status"] = "ok"
            except Unavailable as exc:
                row = {"status": "unavailable", "reason": str(exc), "verdict": "n/a"}
            except subprocess.TimeoutExpired:
                row = {
                    "status": "timeout",
                    "reason": "exceeded the %ds per-document budget" % TIMEOUT,
                    "verdict": "fail",
                }
            except Exception as exc:  # noqa: BLE001 - a crash is a score, not a stop
                row = {
                    "status": "error",
                    "reason": ("%s: %s" % (type(exc).__name__, exc))[:160],
                    "verdict": "fail",
                }
            row["seconds"] = round(time.monotonic() - started, 1)
            apply_budget(row)
            results[cname][sname] = row
            print(
                "  %-24s %-34s %-9s %6ss"
                % (cname, sname, row.get("status"), row["seconds"]),
                flush=True,
            )
            # Checkpoint after EVERY cell. A sweep over the heavy ML engines runs
            # for hours; writing only at the end means a kill loses all of it
            # (which is exactly what happened on the first pass, 19-08-2026).
            if checkpoint:
                checkpoint(results)
    return results


def apply_budget(row: dict[str, Any]) -> dict[str, Any]:
    """Downgrade a cell that produced text but overran the per-document budget.

    Applied to freshly scored cells and to cells carried in through --merge, so a
    matrix assembled over several passes is judged against one budget throughout.
    The ratios stay — they are a real measurement of what the engine returned; only
    the verdict changes, because text that arrives too late is unusable for a
    ~300-article harvest.
    """
    if row.get("status") == "ok" and row.get("seconds", 0) > TIMEOUT:
        row["status"] = "over budget"
        row["reason"] = "returned text in %ss, over the %ds budget" % (
            row["seconds"], TIMEOUT,
        )
        row["verdict"] = "fail"
    return row


def _cell(row: dict[str, Any]) -> str:
    if row["status"] == "unavailable":
        return "unavailable"
    if row["status"] in ("timeout", "over budget"):
        return "over budget (>%ds)" % TIMEOUT
    if row["status"] == "error":
        return "error"
    mark = "PASS" if row["verdict"] == "pass" else "FAIL"
    return "%s cyr %.2f · hit %.2f · w %d" % (
        mark, row["cyrillic_ratio"], row["word_hit_rate"], row["words"],
    )


def report(results: dict[str, Any], names: list[str]) -> str:
    lines = [
        "| Candidate | " + " | ".join(names) + " | passes |",
        "|---|" + "---|" * (len(names) + 1),
    ]
    for cname in CANDIDATES:
        per = results.get(cname)
        if not per:
            continue
        passes = sum(1 for r in per.values() if r.get("verdict") == "pass")
        cells = [_cell(per[n]) if n in per else "not run" for n in names]
        lines.append(
            "| `%s` | %s | **%d/%d** |" % (cname, " | ".join(cells), passes, len(names))
        )
    return "\n".join(lines)


def main() -> int:
    global TIMEOUT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", type=Path, help="directory of galley PDFs (outside the repo)")
    ap.add_argument("--corpus", type=Path, help="private corpus PDFtoTXT directory")
    ap.add_argument("--venv", type=Path, help="throwaway venv for uninstalled candidates (D19)")
    ap.add_argument("--report", action="store_true", help="print the Markdown matrix")
    ap.add_argument(
        "--timeout", type=int, default=TIMEOUT,
        help="per-document budget in seconds (default %d); exceeding it scores `timeout`"
        % TIMEOUT,
    )
    ap.add_argument("--json", type=Path, help="write raw scores here")
    ap.add_argument(
        "--only",
        help="comma-separated candidate names to run; the rest are carried over from --merge",
    )
    ap.add_argument(
        "--merge",
        type=Path,
        help="prior --json scores to start from, so one slow candidate can be re-run alone",
    )
    ap.add_argument(
        "--resume", action="store_true",
        help="skip cells already scored in --merge, so an interrupted sweep can continue",
    )
    ap.add_argument(
        "--latin-samples",
        default="",
        help=(
            "comma-separated sample names that are NOT in Russian; scored against the "
            "English heuristic so a cleanly extracted English article does not read as "
            "a Cyrillic extraction failure"
        ),
    )
    args = ap.parse_args()
    TIMEOUT = args.timeout

    if args.venv:
        exe = args.venv / "Scripts" / "python.exe"
        if not exe.exists():
            exe = args.venv / "bin" / "python"
        _VenvCandidate.python = str(exe)

    samples = collect_samples(args.samples, args.corpus)
    if not samples:
        print("no samples found — pass --samples and/or --corpus", file=sys.stderr)
        return 2
    only = {c.strip() for c in args.only.split(",")} if args.only else None
    if only:
        unknown = only - set(CANDIDATES)
        if unknown:
            print("unknown candidate(s): %s" % ", ".join(sorted(unknown)), file=sys.stderr)
            return 2
    print(
        "%d samples x %d candidates\n" % (len(samples), len(only or CANDIDATES)),
        flush=True,
    )

    results: dict[str, Any] = {}
    merged_names: list[str] = []
    latin = {s.strip() for s in args.latin_samples.split(",") if s.strip()}
    if args.merge and args.merge.exists():
        prior = json.loads(args.merge.read_text(encoding="utf-8"))
        results.update(prior["results"])
        merged_names = prior.get("samples", [])
        # Re-judge carried-over cells against the CURRENT thresholds, so a matrix
        # assembled over several passes cannot mix two calibrations.
        for per in results.values():
            for sname, row in per.items():
                if row.get("status") == "ok":
                    row["verdict"] = verdict_for(row, expect_cyrillic=sname not in latin)
                    apply_budget(row)
    sample_names = merged_names + [s for s, _ in samples if s not in merged_names]

    def write(payload: dict[str, Any]) -> None:
        if not args.json:
            return
        merged = {k: dict(v) for k, v in results.items()}
        for cname, per in payload.items():
            merged.setdefault(cname, {}).update(per)
        args.json.write_text(
            json.dumps({"samples": sample_names, "results": merged},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Cell-level, so re-running one candidate over one sample patches that cell
    # instead of blanking every other sample for that candidate.
    done = results if args.resume else None
    for cname, per in score_all(samples, only, latin, write, done).items():
        results.setdefault(cname, {}).update(per)
    if args.json:
        args.json.write_text(
            json.dumps(
                {"samples": sample_names, "results": results},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
    if args.report:
        print("\n" + report(results, sample_names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
