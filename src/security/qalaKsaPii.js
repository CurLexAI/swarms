// Qal'a (قلعة) — Q5 Sovereign KSA-PII Detector (Node side).
//
// Detects Saudi-specific identifiers in text payloads. Distinct from
// generic secret detection in sovereignCyberRadar.SECRET_PATTERNS and
// adapter SENSITIVE_PATTERNS.
//
// Raw match values are NEVER returned. Each hit is reported as
// { category, maskedValue, span } where maskedValue preserves only the
// first/last two characters with the middle replaced by "…". Callers
// may pass results to the Q7 audit sink without re-redaction.
//
// No network calls. No persistent state. No background workers.
//
// See docs/decisions/ADR-0003-qala-security-architecture.md §Q5.
// Word-boundary discipline: 10-digit shapes (National ID, Iqama, CR)
// overlap heavily, so we anchor with (?<!\d) and (?!\d) to avoid
// matching substrings of longer digit runs.
const IBAN_RE = /\bSA\d{22}\b/g;
const NATIONAL_ID_RE = /(?<!\d)1\d{9}(?!\d)/g;
const IQAMA_RE = /(?<!\d)2\d{9}(?!\d)/g;
const CR_RE = /(?<!\d)7\d{9}(?!\d)/g;
const AMBIGUOUS_10DIGIT_RE = /(?<!\d)[3-689]\d{9}(?!\d)/g;
const MOBILE_RE = /(?<!\d)(?:\+?966\s?5\d{8}|05\d{8})(?!\d)/g;
function maskValue(value) {
    if (value.length < 4)
        return "…";
    return `${value.slice(0, 2)}…${value.slice(-2)}`;
}
function scan(source, pattern, category) {
    const hits = [];
    // Always reset lastIndex before iterating to keep the function pure.
    pattern.lastIndex = 0;
    let match = pattern.exec(source);
    while (match !== null) {
        const start = match.index;
        const end = start + match[0].length;
        hits.push({
            category,
            maskedValue: maskValue(match[0]),
            span: [start, end],
        });
        match = pattern.exec(source);
    }
    return hits;
}
export function detectKsaPii(text) {
    if (typeof text !== "string" || text.length === 0)
        return [];
    const consumed = new Set();
    const hits = [];
    function consider(candidates) {
        for (const hit of candidates) {
            const key = `${hit.span[0]}:${hit.span[1]}`;
            if (!consumed.has(key)) {
                consumed.add(key);
                hits.push(hit);
            }
        }
    }
    // Most specific first: IBAN, then mobile (with country-code shape),
    // then 10-digit IDs partitioned by leading digit.
    consider(scan(text, IBAN_RE, "KSA_IBAN"));
    consider(scan(text, MOBILE_RE, "KSA_MOBILE"));
    consider(scan(text, NATIONAL_ID_RE, "KSA_NATIONAL_ID"));
    consider(scan(text, IQAMA_RE, "KSA_IQAMA"));
    consider(scan(text, CR_RE, "KSA_COMMERCIAL_REGISTRATION"));
    consider(scan(text, AMBIGUOUS_10DIGIT_RE, "KSA_ID_AMBIGUOUS_10DIGIT"));
    hits.sort((a, b) => a.span[0] - b.span[0]);
    return hits;
}
export function hasKsaPii(text) {
    return detectKsaPii(text).length > 0;
}
export function redactKsaPii(text) {
    const hits = detectKsaPii(text);
    if (hits.length === 0)
        return text;
    const pieces = [];
    let cursor = 0;
    for (const hit of hits) {
        const [start, end] = hit.span;
        pieces.push(text.slice(cursor, start));
        pieces.push(`[${hit.category}:${hit.maskedValue}]`);
        cursor = end;
    }
    pieces.push(text.slice(cursor));
    return pieces.join("");
}
