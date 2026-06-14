/**
 * Port of the engine's translit_lint.py — deterministic Sanskrit transliteration
 * linter. Five finding types, anchored to segment span ids. Never rewrites text.
 *
 * Parity with the Python engine is enforced by test/parity.test.ts against golden
 * fixtures produced by `rws lint-translit --json`. Messages are copied verbatim
 * (incl. « » guillemets and — dashes) so the comparison can include the message.
 */

import type {
  Finding,
  FindingType,
  JournalProfile,
  LintResult,
  Segment,
  Severity,
  Term,
} from "./types.ts";
import { normalizeDocument, segmentMarkdown } from "./segment.ts";

const IAST_DIACRITICS = new Set(
  "āīūṛṝḷḹṃḥṅñṭḍṇśṣĀĪŪṚṜḶḸṂḤṄÑṬḌṆŚṢ"
);

// NOTE: regexes used with .test()/.exec() must NOT carry the global flag (it is
// stateful across calls). Only WORD_RE is global, and only via String.match.
const DEVANAGARI_RE = /[ऀ-ॿ]/;
// A dependent vowel sign / virama (U+093A–U+094D, U+0962, U+0963) with no
// preceding consonant — an OCR artifact.
const ORPHAN_MATRA_RE = /(?:^|[\s(«"'])[ऺ-्ॢॣ]/;
export const WORD_PATTERN = "[\\p{L}\\p{M}]+(?:['’\\-][\\p{L}\\p{M}]+)*";
const WORD_RE = new RegExp(WORD_PATTERN, "gu");
// Harvard-Kyoto markers: a capital HK consonant after the first position, or a
// doubled long vowel.
const HK_MARKER_RE = /.[AIURTDNSGJMHLZ]|aa|ii|uu/;
const CYRILLIC_RE = /[Ѐ-ӿ]/;
const LATIN_BASIC_RE = /[a-zA-Z]/;
const SPLIT_TOKEN_RE = /['’\-‐‑‒–]/;

const RU_VOWELS = "аеёиоуыэюя";
const RU_ENDINGS = new Set([
  "", "а", "я", "у", "ю", "е", "и", "ы", "о", "ой", "ей", "ам", "ям",
  "ах", "ях", "ом", "ем", "ов", "ев", "ами", "ями",
]);

export const FINDING_TYPES: FindingType[] = [
  "mixed_transliteration_scheme",
  "inconsistent_term_rendering",
  "missing_iast_on_first_mention",
  "devanagari_nfc_issue",
  "iast_in_cyrillic_word",
];

export function hasCyrillic(word: string): boolean {
  return CYRILLIC_RE.test(word);
}

function hasLatin(word: string): boolean {
  if (LATIN_BASIC_RE.test(word)) return true;
  for (const ch of word) if (IAST_DIACRITICS.has(ch)) return true;
  return false;
}

function isIastWord(word: string): boolean {
  for (const ch of word) if (IAST_DIACRITICS.has(ch)) return true;
  return false;
}

/** True only if a hyphen/apostrophe-separated sub-token fuses Cyrillic + Latin
 *  in one piece (e.g. «бхāшья»). Mono-script hyphenated parts are legitimate. */
function hasFusedMixedToken(word: string): boolean {
  for (const token of word.split(SPLIT_TOKEN_RE)) {
    if (token && hasCyrillic(token) && hasLatin(token)) return true;
  }
  return false;
}

/** ASCII skeleton: lowercase, diacritics stripped (kṛṣṇa -> krsna). */
function skeleton(word: string): string {
  const decomposed = word.toLowerCase().normalize("NFD");
  let out = "";
  for (const ch of decomposed) if (ch >= "a" && ch <= "z") out += ch;
  return out;
}

function ruStem(ru: string): string {
  const last = ru.slice(-1);
  return ru && (RU_VOWELS.includes(last) || last === "ь") ? ru.slice(0, -1) : ru;
}

export function matchesRuTerm(word: string, termRu: string): boolean {
  const w = word.toLowerCase();
  const stem = ruStem(termRu.toLowerCase());
  if (!w.startsWith(stem)) return false;
  return RU_ENDINGS.has(w.slice(stem.length));
}

function words(text: string): string[] {
  return text.match(WORD_RE) ?? [];
}

function finding(
  spanId: string,
  type: FindingType,
  message: string,
  severity: Severity,
  fragment = "",
  term = ""
): Finding {
  const item: Finding = { span_id: spanId, type, message, severity };
  if (fragment) item.fragment = fragment;
  if (term) item.term = term;
  return item;
}

export function lintSegments(
  segments: Segment[],
  terms: Term[],
  profile?: JournalProfile | null
): LintResult {
  const firstMentionRule = profile?.first_mention_rule ?? "ru+iast";
  const requireIastFirstMention =
    firstMentionRule === "ru+iast" || firstMentionRule === "iast+ru";
  const properNouns = new Set(terms.filter((t) => t.proper_noun).map((t) => t.ru));

  const findings: Finding[] = [];
  const iastExamples: string[] = [];
  const hkExamples: Array<[string, string]> = [];
  const termSkeletons = new Map<string, Term>();
  for (const t of terms) termSkeletons.set(skeleton(t.iast), t);

  const ruSeen = new Map<string, string[]>();
  const iastSeen = new Map<string, string[]>();
  for (const t of terms) {
    ruSeen.set(t.ru, []);
    iastSeen.set(t.ru, []);
  }
  const firstMentionFlagged = new Set<string>();

  const prose = segments.filter((s) => !s.span_id.startsWith("c") && s.text);

  for (const seg of prose) {
    const spanId = seg.span_id;
    const text = seg.text;

    if (DEVANAGARI_RE.test(text)) {
      if (text !== text.normalize("NFC")) {
        findings.push(
          finding(
            spanId,
            "devanagari_nfc_issue",
            "Деванагари не в форме NFC: возможна потеря огласовок при поиске и сравнении.",
            "error"
          )
        );
      }
      const orphan = ORPHAN_MATRA_RE.exec(text);
      if (orphan) {
        findings.push(
          finding(
            spanId,
            "devanagari_nfc_issue",
            "Огласовка деванагари без опорного согласного (вероятный артефакт OCR).",
            "error",
            orphan[0].trim()
          )
        );
      }
    }

    for (const word of words(text)) {
      const cyr = hasCyrillic(word);
      const lat = hasLatin(word);

      if (cyr && lat && hasFusedMixedToken(word)) {
        findings.push(
          finding(
            spanId,
            "iast_in_cyrillic_word",
            `Смешение кириллицы и латиницы внутри словоформы: «${word}».`,
            "error",
            word
          )
        );
        continue;
      }

      if (lat && isIastWord(word)) {
        iastExamples.push(word);
      } else if (lat && HK_MARKER_RE.test(word)) {
        if (termSkeletons.has(skeleton(word))) hkExamples.push([spanId, word]);
      }
    }

    const lowered = text.toLowerCase();
    const loweredWords = words(lowered);
    for (const term of terms) {
      const ru = term.ru;
      const iast = term.iast.toLowerCase();
      if (lowered.includes(iast)) iastSeen.get(ru)!.push(spanId);
      const ruHit = loweredWords.some((w) => hasCyrillic(w) && matchesRuTerm(w, ru));
      if (ruHit) {
        ruSeen.get(ru)!.push(spanId);
        const firstEver = ruSeen.get(ru)!.length === 1 && iastSeen.get(ru)!.length === 0;
        if (
          requireIastFirstMention &&
          !properNouns.has(ru) &&
          firstEver &&
          !lowered.includes(iast) &&
          !firstMentionFlagged.has(ru)
        ) {
          firstMentionFlagged.add(ru);
          findings.push(
            finding(
              spanId,
              "missing_iast_on_first_mention",
              `Первое упоминание термина «${ru}» без IAST в скобках: ожидается «${ru} (${term.iast})».`,
              "warning",
              "",
              ru
            )
          );
        }
      }
    }
  }

  if (iastExamples.length > 0 && hkExamples.length > 0) {
    const [spanId, hkWord] = hkExamples[0];
    findings.push(
      finding(
        spanId,
        "mixed_transliteration_scheme",
        `В тексте смешаны схемы транслитерации: IAST (напр., «${iastExamples[0]}») и Harvard-Kyoto (напр., «${hkWord}»). Приведите к одной схеме (для журналов — IAST).`,
        "error",
        hkWord
      )
    );
  }

  for (const term of terms) {
    const ru = term.ru;
    if (properNouns.has(ru)) continue;
    const ruList = ruSeen.get(ru)!;
    const unpairedIast = iastSeen.get(ru)!.filter((s) => !ruList.includes(s));
    if (ruList.length >= 2 && unpairedIast.length >= 2) {
      findings.push(
        finding(
          unpairedIast[0],
          "inconsistent_term_rendering",
          `Термин передается то кириллицей («${ru}»), то латиницей («${term.iast}») без системы; выберите основную форму, вторую давайте в скобках при первом упоминании.`,
          "warning",
          "",
          ru
        )
      );
    }
  }

  const findingCounts = {} as Record<FindingType, number>;
  for (const ftype of FINDING_TYPES) {
    findingCounts[ftype] = findings.filter((f) => f.type === ftype).length;
  }
  const schemes = [
    ...(iastExamples.length ? ["iast"] : []),
    ...(hkExamples.length ? ["harvard-kyoto"] : []),
  ].sort();

  return {
    status: "completed",
    findings,
    summary: {
      segments_checked: prose.length,
      iast_word_count: iastExamples.length,
      hk_word_count: hkExamples.length,
      schemes_detected: schemes,
      finding_counts: findingCounts,
    },
  };
}

/** Normalize + segment Markdown text and lint it (engine lint_text). */
export function lintText(
  text: string,
  terms: Term[],
  profile?: JournalProfile | null
): LintResult {
  // The NFC check must run on the raw input: normalizeDocument applies NFC,
  // which would mask the problem in the source.
  const rawNfcIssue = DEVANAGARI_RE.test(text) && text !== text.normalize("NFC");

  const normalized = normalizeDocument(text);
  const segments = segmentMarkdown(normalized);
  const result = lintSegments(segments, terms, profile);

  if (rawNfcIssue) {
    const anchor =
      segments.find((s) => DEVANAGARI_RE.test(s.text))?.span_id ??
      segments[0]?.span_id ??
      "p001";
    result.findings.unshift(
      finding(
        anchor,
        "devanagari_nfc_issue",
        "Исходный файл содержит деванагари не в форме NFC: нормализуйте файл (NFC), иначе поиск и сравнение строк ненадежны.",
        "error"
      )
    );
    result.summary.finding_counts.devanagari_nfc_issue += 1;
  }
  return result;
}
