"""
Parse tab-delimited text pasted from Excel into a pandas DataFrame.

Responsibilities:
- Split pasted text into rows/columns (tab-delimited)
- Detect and normalize header row
- Validate required columns are present
- Return DataFrame with canonical column names plus warnings list
"""

from __future__ import annotations

import re
from io import StringIO
from typing import NamedTuple

import pandas as pd

# ---------------------------------------------------------------------------
# Canonical column names used throughout the app
# ---------------------------------------------------------------------------
COL_CLIENT = "Client Name"
COL_MRN = "MRN"
COL_DOS = "Date of Service"
COL_SERVICE = "Service Type"
COL_PAYMENT_DATE = "Payment Date"
COL_CHARGE = "Charge Amount"
COL_PAYMENT_TYPE = "Payment Type"
COL_RECEIPT = "Receipt Saved"
COL_COMMENT = "Comment"

REQUIRED_COLS = [COL_DOS, COL_SERVICE, COL_CHARGE]

# ---------------------------------------------------------------------------
# Mapping from normalized header text → canonical column name
# Covers common misspellings and spacing variants
# ---------------------------------------------------------------------------
_HEADER_MAP: dict[str, str] = {
    "client name": COL_CLIENT,
    "clientname": COL_CLIENT,
    "mrn": COL_MRN,
    "date of service": COL_DOS,
    "dateofservice": COL_DOS,
    "dos": COL_DOS,
    "service type": COL_SERVICE,
    "servicetype": COL_SERVICE,
    "payment date": COL_PAYMENT_DATE,
    "paymentdate": COL_PAYMENT_DATE,
    "charge amount": COL_CHARGE,
    "chargeamount": COL_CHARGE,
    "charge": COL_CHARGE,
    "payment type": COL_PAYMENT_TYPE,
    "paymenttype": COL_PAYMENT_TYPE,
    "receipt saved": COL_RECEIPT,
    "receiptsaved": COL_RECEIPT,
    # Common misspelling
    "reciept saved": COL_RECEIPT,
    "received saved": COL_RECEIPT,
    "comment": COL_COMMENT,
    "comments": COL_COMMENT,
}

# Keywords that indicate a row is likely a header row
_HEADER_KEYWORDS = {
    "mrn", "date of service", "service type",
    "charge amount", "client name", "payment date",
    "receipt saved", "reciept saved", "comment",
}

# Inferred column layouts for headerless pastes keyed by column count
_INFERRED_LAYOUTS: dict[int, list[str]] = {
    4: [COL_DOS, COL_SERVICE, COL_PAYMENT_DATE, COL_CHARGE],
    5: [COL_MRN, COL_DOS, COL_SERVICE, COL_PAYMENT_DATE, COL_CHARGE],
    9: [
        COL_CLIENT, COL_MRN, COL_DOS, COL_SERVICE,
        COL_PAYMENT_DATE, COL_CHARGE, COL_PAYMENT_TYPE,
        COL_RECEIPT, COL_COMMENT,
    ],
}

_INFERRED_LAYOUT_NAMES: dict[int, str] = {
    4: "4-column layout: Date of Service, Service Type, Payment Date, Charge Amount",
    5: "5-column layout: MRN, Date of Service, Service Type, Payment Date, Charge Amount",
    9: (
        "9-column layout: Client Name, MRN, Date of Service, Service Type, "
        "Payment Date, Charge Amount, Payment Type, Receipt Saved, Comment"
    ),
}


def _normalize_header_text(text: str) -> str:
    """Lowercase + strip whitespace."""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _looks_like_header(row: list[str]) -> bool:
    """Return True if the row appears to be a header row."""
    normalized = {_normalize_header_text(cell) for cell in row}
    matches = normalized & _HEADER_KEYWORDS
    return len(matches) >= 2


def _map_header(raw_name: str) -> str:
    """Map a raw header cell to a canonical column name (or keep as-is)."""
    key = _normalize_header_text(raw_name)
    return _HEADER_MAP.get(key, raw_name.strip())


class ParseResult(NamedTuple):
    df: pd.DataFrame
    warnings: list[str]
    errors: list[str]


def parse_pasted_text(text: str) -> ParseResult:
    """
    Parse a tab-delimited string (pasted from Excel) into a DataFrame.

    Returns a ParseResult with:
    - df: the parsed DataFrame with canonical column names
    - warnings: non-fatal issues
    - errors: fatal issues (df will be empty if errors exist)
    """
    warnings: list[str] = []
    errors: list[str] = []

    if not text or not text.strip():
        errors.append("No data pasted.")
        return ParseResult(pd.DataFrame(), warnings, errors)

    # Split into non-empty lines
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        errors.append("No data pasted.")
        return ParseResult(pd.DataFrame(), warnings, errors)

    # Split each line into tab-delimited cells
    rows = [line.split("\t") for line in lines]

    # Detect header row
    has_header = _looks_like_header(rows[0])

    if has_header:
        raw_headers = rows[0]
        data_rows = rows[1:]
    else:
        # No header detected – infer column layout from column count
        ncols = len(rows[0])
        if ncols in _INFERRED_LAYOUTS:
            inferred = _INFERRED_LAYOUTS[ncols]
            layout_name = _INFERRED_LAYOUT_NAMES[ncols]
        else:
            # Fallback: map as many 9-column names as available
            inferred = _INFERRED_LAYOUTS[9]
            layout_name = _INFERRED_LAYOUT_NAMES[9]
        raw_headers = inferred[:ncols]
        warnings.append(
            f"No header row detected. Using inferred {layout_name}."
        )
        data_rows = rows

    # Map raw headers to canonical names
    headers = [_map_header(h) for h in raw_headers]

    if not data_rows:
        errors.append("Header row found but no data rows.")
        return ParseResult(pd.DataFrame(), warnings, errors)

    # Pad / trim each data row to match header length
    ncols = len(headers)
    padded_rows = []
    for row in data_rows:
        if len(row) < ncols:
            row = row + [""] * (ncols - len(row))
        elif len(row) > ncols:
            row = row[:ncols]
        padded_rows.append(row)

    df = pd.DataFrame(padded_rows, columns=headers)

    # -----------------------------------------------------------------------
    # Validate required columns
    # -----------------------------------------------------------------------
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        errors.append(f"Missing required column(s): {', '.join(missing)}")
        return ParseResult(pd.DataFrame(), warnings, errors)

    # -----------------------------------------------------------------------
    # Coerce charge amounts
    # -----------------------------------------------------------------------
    original_charges = df[COL_CHARGE].astype(str).copy()
    cleaned_charges = original_charges.str.replace(r"[$,]", "", regex=True).str.strip()
    numeric_charges = pd.to_numeric(cleaned_charges, errors="coerce")

    bad_charge_mask = numeric_charges.isna() & original_charges.str.strip().ne("")
    if bad_charge_mask.any():
        bad_vals = original_charges[bad_charge_mask].unique().tolist()
        warnings.append(
            f"Non-numeric charge value(s) coerced to 0: {bad_vals}"
        )
    df[COL_CHARGE] = numeric_charges.fillna(0.0)

    # -----------------------------------------------------------------------
    # Parse dates – keep original strings for display, add _parsed column
    # -----------------------------------------------------------------------
    def _parse_date(val: str):
        s = str(val).strip()
        if not s:
            return None
        try:
            return pd.to_datetime(s, dayfirst=False)
        except Exception:
            return None

    df["_dos_parsed"] = df[COL_DOS].apply(_parse_date)

    blank_dos = df["_dos_parsed"].isna() & df[COL_DOS].str.strip().ne("")
    if blank_dos.any():
        bad_dates = df.loc[blank_dos, COL_DOS].unique().tolist()
        warnings.append(f"Unparseable date value(s) (will use row order): {bad_dates}")

    truly_blank_dos = df[COL_DOS].str.strip().eq("")
    if truly_blank_dos.any():
        warnings.append(
            f"{truly_blank_dos.sum()} row(s) have blank Date of Service."
        )

    # -----------------------------------------------------------------------
    # Warn about missing or blank MRNs
    # -----------------------------------------------------------------------
    if COL_MRN not in df.columns:
        warnings.append("No MRN column detected. Each row was processed independently.")
    else:
        blank_mrn = df[COL_MRN].str.strip().eq("")
        if blank_mrn.any():
            warnings.append(f"{blank_mrn.sum()} row(s) have blank MRN.")

        # -------------------------------------------------------------------
        # Warn about MRNs with multiple rows
        # -------------------------------------------------------------------
        mrn_counts = df[COL_MRN].value_counts()
        multi_mrn = mrn_counts[mrn_counts > 1].index.tolist()
        if multi_mrn:
            warnings.append(
                f"MRN(s) with multiple rows: {', '.join(str(m) for m in multi_mrn)}"
            )

    return ParseResult(df, warnings, errors)
