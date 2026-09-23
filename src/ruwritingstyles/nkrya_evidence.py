"""NKRYa (Russian National Corpus) evidence for RuWritingStyles (H5283).

Two uses, both advisory — nothing here accepts or rejects a text:

1. Keyness for a style passport: the top content lemmas of a source text, each
   with its NKRYa frequency (word portrait, main corpus, ipm + band 1..6), ranked
   by log-ratio keyness log2(ipm in text / ipm in NKRYa).
2. Anachronism evidence for scrutiny: modern ipm + hits in the 1800-1899 slice
   of the main corpus, attached to a lexical-anachronism finding.

Offline by default. Cached responses live in `metadata/nkrya_cache/` and are
read here without the network, keyed exactly as the NKRYa client keys them
(sha256 of endpoint + payload), so CI never needs a token or the client.
Live fetches (`offline=False`) go through the official-API client: csl-pyutil's
shared `nkrya` module when it is installed (H5282), otherwise — temporarily —
SanskritLexicography's `RussianTranslation/src/nkrya_client.py` by path.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

SEED = 5261  # the client's fixed seed; part of every cache key
SLICE_19C = {"fieldName": "created", "intRange": {"begin": 1800, "end": 1899}}
LIVE_MIN_INTERVAL_S = 10.0  # ~6 requests/min: NKRYa answered 429 after ~10/min (23-09-2026)
IPM_FLOOR = 0.01  # reference ipm used when NKRYa has no portrait for a lemma
DEFAULT_CACHE_REL = Path("metadata") / "nkrya_cache"
CLIENT_ENV = "RWS_NKRYA_CLIENT"
SIBLING_CLIENT = Path("SanskritLexicography") / "RussianTranslation" / "src" / "nkrya_client.py"

# pymorphy POS -> NKRYa POS. Participles and gerunds are skipped: NKRYa folds
# them into the verb lemma, pymorphy does not.
POS_MAP = {"NOUN": "S", "ADJF": "A", "ADJS": "A", "COMP": "A", "INFN": "V", "VERB": "V", "ADVB": "ADV"}
POS_RU = {"S": "сущ.", "A": "прил.", "V": "гл.", "ADV": "нареч."}
# Light verbs and quantifier-like adjectives/adverbs pymorphy tags as content words.
STOP_LEMMAS = frozenset(
    "быть мочь стать иметь являться весь свой самый другой такой один так также ещё еще "
    "очень уже более менее можно нужно лишь только тоже впрочем именно почти вообще "
    "есть здесь где там тут когда тогда потом теперь сейчас".split()
)
WORD_RE = re.compile(r"[А-Яа-яЁёѢѣІіѲѳѴѵ]+(?:-[А-Яа-яЁёѢѣІіѲѳѴѵ]+)*")
PRE_REFORM = str.maketrans({"ѣ": "е", "Ѣ": "Е", "і": "и", "І": "И", "ѳ": "ф", "Ѳ": "Ф", "ѵ": "и", "Ѵ": "И"})
# stress marks: combining accents, and the \x01/\x02 control bytes the Ударение-2019 extraction left inside words
STRESS_MARKS = re.compile("[\u0000-\u0008\u000e-\u001f\u0300-\u036f]")
FINAL_HARD_SIGN = re.compile(r"(?<=[бвгджзклмнпрстфхцчшщ])ъ\b", re.IGNORECASE)


def yo_fold(s: str) -> str:
    return s.replace("ё", "е").replace("Ё", "Е") if s else s


def modernize_orthography(text: str) -> str:
    """Pre-1918 spelling -> modern (ѣ->е, і->и, ѳ->ф, ѵ->и, word-final ъ dropped); stress marks stripped."""
    return FINAL_HARD_SIGN.sub("", STRESS_MARKS.sub("", text).translate(PRE_REFORM))


def request_key(endpoint: str, payload: dict) -> str:
    blob = json.dumps({"endpoint": endpoint, "payload": payload},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def portrait_payload(lemma: str, pos: str | None, result_type: str, corpus: str = "MAIN") -> dict:
    payload: dict[str, Any] = {"lemma": yo_fold(lemma), "corpus": {"type": corpus},
                               "resultType": [result_type], "seed": SEED}
    if pos:
        payload["pos"] = pos
    return payload


def lemma_query(lemma: str) -> dict:
    return {"sectionValues": [{"subsectionValues": [
        {"conditionValues": [{"fieldName": "lex", "text": {"v": lemma}}]}]}]}


def concordance_payload(lexgramm: dict, n: int = 1, corpus: str = "MAIN",
                        subcorpus_conditions: list | None = None) -> dict:
    payload: dict[str, Any] = {"corpus": {"type": corpus}, "lexGramm": lexgramm,
                               "params": {"pageParams": {"page": 0, "docsPerPage": n, "snippetsPerDoc": 1},
                                          "seed": SEED}}
    if subcorpus_conditions:
        payload["subcorpus"] = {"sectionValues": [{"conditionValues": list(subcorpus_conditions)}]}
    return payload


class NkryaUnavailable(RuntimeError):
    """Offline cache miss, or no live client to fetch with."""


def _load_client_module(repo_root: Path | None) -> Any:
    try:  # H5282: the shared client, once csl-pyutil ships it
        from csl_pyutil import nkrya  # type: ignore[import-not-found]
        return nkrya
    except ImportError:
        pass
    candidates = [os.environ.get(CLIENT_ENV, "")]
    if repo_root is not None:
        # a worktree sits beside its main checkout, so the sibling is one level up either way
        candidates.append(str(repo_root.resolve().parent / SIBLING_CLIENT))
    for cand in candidates:
        if cand and Path(cand).is_file():
            spec = importlib.util.spec_from_file_location("rws_nkrya_client", cand)
            module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            return module
    raise NkryaUnavailable(
        "no NKRYa client: install csl-pyutil with the nkrya module (H5282), or set "
        f"{CLIENT_ENV} to SanskritLexicography/RussianTranslation/src/nkrya_client.py")


class NkryaEvidence:
    """Cache-first NKRYa lookups. offline=True never touches the network."""

    def __init__(self, cache_dir: Path, *, offline: bool = True, repo_root: Path | None = None):
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.used_keys: list[str] = []
        self._client = None
        self._repo_root = repo_root

    def _live(self) -> Any:
        if self._client is None:
            mod = _load_client_module(self._repo_root)
            if getattr(mod, "MIN_INTERVAL_S", LIVE_MIN_INTERVAL_S) < LIVE_MIN_INTERVAL_S:
                mod.MIN_INTERVAL_S = LIVE_MIN_INTERVAL_S  # the by-path client sleeps only 1 s
                mod.MAX_RETRIES = max(getattr(mod, "MAX_RETRIES", 3), 5)
            self._client = mod.NkryaClient(cache_dir=str(self.cache_dir), offline=False)
        return self._client

    def _get(self, endpoint: str, payload: dict, method: str) -> dict:
        key = request_key(endpoint, payload)
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            if self.offline:
                raise NkryaUnavailable(f"not cached (offline): {endpoint} {key}")
            self._live()._call(endpoint, payload, method)
        self.used_keys.append(key)
        return json.loads(path.read_text(encoding="utf-8"))["response"]

    def freq(self, lemma: str, pos: str | None = None) -> dict:
        raw = self._get("/word-portrait/", portrait_payload(lemma, pos, "PORTRAIT_FREQUENCY"), "GET")
        fd = raw.get("frequencyData") or {}
        return {"ipm": fd.get("ipm"), "category": fd.get("category")}

    def hits_19c(self, lemma: str) -> int | None:
        payload = concordance_payload(lemma_query(lemma), n=1, subcorpus_conditions=[SLICE_19C])
        raw = self._get("/lex-gramm/concordance", payload, "POST")
        return (raw.get("queryStats") or {}).get("wordUsageCount")


# ---- keyness ---------------------------------------------------------------

@dataclass
class LemmaCounts:
    tokens: int = 0
    counts: Counter = field(default_factory=Counter)


def count_content_lemmas(text: str, morph: Any = None) -> LemmaCounts:
    """Tokenize + lemmatize (pymorphy3); count content lemmas keyed (lemma, NKRYa POS)."""
    if morph is None:
        import pymorphy3  # optional extra: pip install ruwritingstyles[nkrya]
        morph = pymorphy3.MorphAnalyzer()
    cache: dict[str, tuple[str, str] | None] = {}
    out = LemmaCounts()
    text = modernize_orthography(text)
    for m in WORD_RE.finditer(text):
        word = m.group(0).lower()
        out.tokens += 1
        if m.group(0)[0].isupper() and text[m.end():m.end() + 1] == ".":
            continue  # a siglum/abbreviation («Чуд.», «Феод.», «Сух.»), not a word of the text
        if word not in cache:
            cache[word] = _content_lemma(morph, word)
        hit = cache[word]
        if hit:
            out.counts[hit] += 1
    return out


def _content_lemma(morph: Any, word: str) -> tuple[str, str] | None:
    if len(word) < 3:
        return None
    parse = morph.parse(word)[0]
    tag = parse.tag
    pos = POS_MAP.get(tag.POS or "")
    if not pos or not parse.is_known:
        return None
    if {"Apro", "Anum", "Abbr", "Init", "Name", "Surn", "Patr"} & set(tag.grammemes):
        return None
    lemma = parse.normal_form
    if lemma in STOP_LEMMAS:
        return None
    return lemma, pos


def log_ratio(count: int, tokens: int, ref_ipm: float | None) -> float:
    """log2(ipm in text / ipm in NKRYa); a missing/zero reference uses IPM_FLOOR."""
    text_ipm = count / tokens * 1_000_000
    return math.log2(text_ipm / max(ref_ipm or 0.0, IPM_FLOOR))


def keyness_rows(counts: LemmaCounts, evidence: NkryaEvidence, top_n: int) -> list[dict]:
    rows = []
    for (lemma, pos), n in counts.counts.most_common(top_n):
        f = evidence.freq(lemma, pos)
        rows.append({
            "lemma": lemma, "pos": pos, "count": n,
            "text_ipm": round(n / counts.tokens * 1_000_000, 1),
            "nkrya_ipm": f["ipm"], "band": f["category"],
            "log_ratio": round(log_ratio(n, counts.tokens, f["ipm"]), 2),
        })
    rows.sort(key=lambda r: -r["log_ratio"])
    return rows


SECTION_START = "<!-- nkrya-keyness:start (H5283, generated by scripts/nkrya_keyness.py) -->"
SECTION_END = "<!-- nkrya-keyness:end -->"


def render_section(report: dict) -> str:
    rows = report["rows"]
    lines = [
        SECTION_START,
        "## Лексическая подпись (НКРЯ)",
        "",
        f"_Измерено {report['measured']} (H5283): {report['source_label']} — "
        f"{report['tokens']:,} словоупотреблений".replace(",", " ")
        + f", {len(rows)} самых частых знаменательных лемм (pymorphy3). "
        "Частота НКРЯ — портрет слова в основном корпусе: ipm и полоса 1–6 "
        "(1 — реже 1 ipm … 6 — чаще 10 000 ipm). "
        "Ключевость — log₂(ipm в тексте / ipm в НКРЯ): +3 значит «в 8 раз чаще, чем в языке вообще». "
        f"Отчёт и кэш запросов: [{report['report_rel']}]({report['report_url']})._",
        "",
        "| Лемма | Ч. р. | В тексте | ipm в тексте | ipm НКРЯ | Полоса | Ключевость |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        ref = "нет портрета" if r["nkrya_ipm"] is None else f"{r['nkrya_ipm']:g}"
        band = "—" if r["band"] is None else str(r["band"])
        lines.append(f"| {r['lemma']} | {POS_RU[r['pos']]} | {r['count']} | {r['text_ipm']:g} | "
                     f"{ref} | {band} | {r['log_ratio']:+.2f} |")
    top = [r["lemma"] for r in rows[:5]]
    common = [r["lemma"] for r in rows if r["log_ratio"] < 1][:5]
    lines += ["", f"**Как читать.** Ядро подписи — {', '.join(top)}: это слова, ради которых текст "
              "узнаётся. " + (f"Обычные для языка слова ({', '.join(common)}) частотны и здесь, но не отличают стиль. "
                              if common else "")
              + "Таблица — измерение, а не правило: она подсказывает словарь темы, не требует его.",
              SECTION_END]
    return "\n".join(lines)


def upsert_section(passport_md: str, section: str, before_heading: str | None = None) -> str:
    """Replace an existing generated section, else insert it before `before_heading` (or append)."""
    if SECTION_START in passport_md:
        head, rest = passport_md.split(SECTION_START, 1)
        _, tail = rest.split(SECTION_END, 1)
        return head + section + tail
    if before_heading and f"\n{before_heading}" in passport_md:
        head, tail = passport_md.split(f"\n{before_heading}", 1)
        return head.rstrip("\n") + "\n\n" + section + "\n\n" + before_heading + tail
    return passport_md.rstrip("\n") + "\n\n" + section + "\n"


# ---- anachronism evidence (scrutiny) ---------------------------------------

# Archaic / Church-Slavonic function words pymorphy knows but never marks (its `Arch`
# grammeme is unused in practice) — the usual suspects of pseudo-archaism.
ARCHAIC_SEED = frozenset(
    "сей оный дабы токмо зело паки понеже яко аки ибо доколе дондеже егда иже коий "
    "вельми нонче ныне отселе доселе поелику особливо купно всуе втуне".split()
)
QUOTED_TERM = re.compile(r"[«\"'“‘]([А-Яа-яЁёѢѣІі-]+)[»\"'”’]")


def _morph(morph: Any) -> Any:
    if morph is not None:
        return morph
    try:
        import pymorphy3  # optional extra: pip install ruwritingstyles[nkrya]
    except ImportError:
        return None
    return pymorphy3.MorphAnalyzer()


def lemma_of(word: str, morph: Any = None) -> tuple[str, str | None]:
    """(lemma, NKRYa POS) for one word. Out-of-dictionary words keep their own form:
    pymorphy's guess for an archaism is noise (вельми -> «вельмить»)."""
    word = modernize_orthography(word).lower()
    morph = _morph(morph)
    if morph is None or word in ARCHAIC_SEED:
        return word, None
    parse = morph.parse(word)[0]
    if not parse.is_known:
        return word, None
    if parse.normal_form in ARCHAIC_SEED:
        return parse.normal_form, None
    return parse.normal_form, POS_MAP.get(parse.tag.POS or "")


def anachronism_candidates(text: str, morph: Any = None, limit: int = 20) -> list[tuple[str, str | None]]:
    """Lemmas worth a corpus check, in text order: pre-reform spellings, the archaic seed
    list, and out-of-dictionary words. Empty when pymorphy3 is not installed."""
    morph = _morph(morph)
    if morph is None:
        return []
    seen: dict[tuple[str, str | None], None] = {}
    for m in WORD_RE.finditer(STRESS_MARKS.sub("", text)):
        raw = m.group(0)
        word = modernize_orthography(raw).lower()
        if len(word) < 3 or (raw[0].isupper() and word not in ARCHAIC_SEED):
            continue  # capitalised tokens are mostly names and sigla
        pre_reform = word != raw.lower()
        parse = morph.parse(word)[0]
        if pre_reform or word in ARCHAIC_SEED or parse.normal_form in ARCHAIC_SEED or not parse.is_known:
            seen.setdefault(lemma_of(word, morph), None)
        if len(seen) >= limit:
            break
    return list(seen)


def evidence_hint(ipm: float | None, band: int | None, hits_19c: int | None) -> str:
    if hits_19c == 0 and (ipm or 0) >= 1:
        return "modern-only: no 1800-1899 hits"
    if (band or 0) <= 1 and (hits_19c or 0) > 0:
        return "rare today, attested in 1800-1899 (archaism)"
    if ipm is None and not hits_19c:
        return "unattested in NKRYa main corpus"
    return "no temporal contrast"


def lemma_evidence(evidence: NkryaEvidence, lemma: str, pos: str | None) -> dict:
    row: dict[str, Any] = {"lemma": lemma, "pos": pos, "source": "NKRYa main corpus (ruscorpora.ru API)",
                           "advisory": True}
    try:
        f = evidence.freq(lemma, pos)
        row.update(ipm=f["ipm"], band=f["category"], hits_1800_1899=evidence.hits_19c(lemma))
        row["hint"] = evidence_hint(row["ipm"], row["band"], row["hits_1800_1899"])
    except NkryaUnavailable as exc:
        row.update(status="unavailable", reason=str(exc))
    return row


def attach_nkrya_evidence(findings: Iterable[dict], evidence: NkryaEvidence, morph: Any = None) -> list[dict]:
    """Add `nkrya_evidence` to each anachronism finding. Advisory: severity/confidence untouched."""
    out = []
    for f in findings:
        f = dict(f)
        if f.get("category") == "anachronism":
            term = f.get("term") or next(iter(QUOTED_TERM.findall(f.get("finding", ""))), None)
            if term:
                lemma, pos = lemma_of(term, morph)
                f["nkrya_evidence"] = lemma_evidence(evidence, lemma, pos)
        out.append(f)
    return out


def render_evidence_table(rows: list[dict]) -> str:
    lines = ["| Lemma | POS | NKRYa ipm | Band | Hits 1800–1899 | Hint |", "|---|---|---:|---:|---:|---|"]
    for r in rows:
        if r.get("status") == "unavailable":
            lines.append(f"| {r['lemma']} | {r['pos'] or '—'} | — | — | — | not cached |")
            continue
        ipm = "—" if r["ipm"] is None else f"{r['ipm']:g}"
        band = "—" if r["band"] is None else str(r["band"])
        hits = "—" if r["hits_1800_1899"] is None else str(r["hits_1800_1899"])
        lines.append(f"| {r['lemma']} | {r['pos'] or '—'} | {ipm} | {band} | {hits} | {r['hint']} |")
    return "\n".join(lines)
