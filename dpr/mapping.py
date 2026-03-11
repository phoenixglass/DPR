"""
Service-type → DPR shorthand mapping.

Rules applied in order:
1. Strip NSF prefix  (e.g. "NSF - " or "NSF -")
2. Strip Telemed prefix  (e.g. "Telemed:" or "Telemed OP:")
3. Map remaining core service to a shorthand label
4. Reassemble with NSF / Tele prefixes as appropriate
"""

import re

# ---------------------------------------------------------------------------
# Core service-type patterns → DPR shorthand
# Each entry: (compiled regex, label)
# Order matters – more specific patterns first.
# ---------------------------------------------------------------------------
_CORE_PATTERNS: list[tuple[re.Pattern, str]] = []

_RAW_PATTERNS: list[tuple[str, str]] = [
    # Assessment
    (r"assessment/diag\s*\(bps\)\s*w/o\s*med\s*services", "Assess"),
    # Psych eval (several phrasings)
    (r"psychiatric\s+diag\.?\s+eval\.?\s+w\.?\s+med\s+services", "Psych Eval"),
    (r"psych\s+diag\.?\s+eval\.?\s+w\.?\s+med\s+services", "Psych Eval"),
    # Psych follow-up with medication admin
    (r"op:\s*psych\s+with\s+medication\s+admin/injection", "MAT + Psych f/u"),
    # Psych follow-up – capture time range dynamically
    (r"op:\s*psych\s+appointment\s*\((\d+-\d+)\s+minutes?\)", None),   # special
    (r"op:\s*psych\s+follow[.\s-]up\s*\((\d+-\d+)\s+minutes?\)", None),     # special
    # Medication admin
    (r"medication\s+admin/injection", "MAT"),
    # Group
    (r"outpatient\s+group\s*\(75-90\s+minutes?\)", "group"),
    # EMDR 53+
    (r"outpatient\s+emdr\s+53\+\s*(?:minutes?)?", "IT 53+"),
    # Outpatient individual – order 53+ before 38-52 before 16-37
    (r"outpatient\s+53\+\s*(?:minutes?)?", "IT 53+"),
    (r"outpatient\s+38-52\s*(?:minutes?)?", "IT 38-52"),
    (r"outpatient\s+16-37\s*(?:minutes?)?", "IT 16-37"),
    # Family therapy
    (r"family\s+session\s+w(?:/)?out\s+the\s+client\s+26\+.*", "FT w/out client"),
    (r"family\s+session\s+with\s+client\s+26\+.*", "FT w/client"),
    # IOP variants
    (r"iop[-\s]wilton", "IOP"),
    (r"iop\s+chappaqua", "IOP"),
    (r"iop\s+huntington", "IOP"),
    (r"^iop$", "IOP"),
    # Payment plan
    (r"payment\s+plan", "payment plan"),
]

for _pat, _label in _RAW_PATTERNS:
    _CORE_PATTERNS.append((re.compile(_pat, re.IGNORECASE), _label))

# Regex for Psych f/u dynamic time range (reused in _map_core)
# Two forms:
#   1. "OP: Psych Appointment (30-39 minutes)"  — standard, non-telemed
#   2. "Psych Appointment (30-39 minutes)"       — after Telemed OP: prefix is stripped
_PSYCH_FU_RE = re.compile(
    r"op:\s*psych\s+(?:appointment|follow[.\s-]up)\s*\((\d+-\d+)\s+minutes?\)",
    re.IGNORECASE,
)
_PSYCH_FU_BARE_RE = re.compile(
    r"^psych\s+(?:appointment|follow[.\s-]up)\s*\((\d+-\d+)\s+minutes?\)",
    re.IGNORECASE,
)

# Prefix regexes
_NSF_RE = re.compile(r"^NSF\s*-\s*", re.IGNORECASE)
_TELE_RE = re.compile(r"^Telemed(?:\s+OP)?:\s*", re.IGNORECASE)


def _map_core(text: str) -> tuple[str, bool]:
    """
    Map core service text (after stripping NSF/Telemed prefixes) to a DPR label.

    Returns (label, is_unmapped).
    """
    stripped = text.strip()

    # Dynamic Psych f/u pattern — with or without leading "OP:"
    m = _PSYCH_FU_RE.match(stripped) or _PSYCH_FU_BARE_RE.match(stripped)
    if m:
        return f"Psych f/u {m.group(1)}", False

    for pattern, label in _CORE_PATTERNS:
        if label is None:
            continue  # handled above
        if pattern.search(stripped):
            return label, False

    # No match – return raw text and flag as unmapped
    return stripped, True


def map_service(service_type: str) -> tuple[str, bool]:
    """
    Map a service-type string to a DPR shorthand label.

    Returns:
        (label, is_unmapped)
        is_unmapped=True when no rule matched (raw text preserved).
    """
    if not service_type or (hasattr(service_type, "__class__") and
                             service_type.__class__.__name__ == "float"):
        return "", True

    raw = str(service_type).strip()
    if not raw:
        return "", True

    # --- 1. Detect NSF prefix ---
    nsf = False
    working = raw
    nsf_match = _NSF_RE.match(working)
    if nsf_match:
        nsf = True
        working = working[nsf_match.end():]

    # --- 2. Detect Telemed prefix ---
    tele = False
    tele_match = _TELE_RE.match(working)
    if tele_match:
        tele = True
        working = working[tele_match.end():]

    # --- 3. Map core service ---
    core_label, is_unmapped = _map_core(working)

    # --- 4. Reassemble ---
    parts: list[str] = []
    if nsf:
        parts.append("NSF")
    if tele:
        parts.append("Tele")
    parts.append(core_label)

    return " ".join(parts), is_unmapped
