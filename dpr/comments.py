"""
Generate DPR comments from a parsed DataFrame.

Comment format:
    $TOTAL m/d label, m/d label, m/d label

BUSINESS RULES (must be upheld by every change to this module):
  1. Row order must never change — output rows are in exact paste order.
  2. Each MRN gets exactly one calculated comment.
  3. That comment is written onto every row that shares the MRN.
  4. Comments align exactly with the pasted row order for Excel paste-back.
"""

from __future__ import annotations

import pandas as pd

from dpr.mapping import map_service
from dpr.parser import COL_MRN, COL_DOS, COL_SERVICE, COL_CHARGE

COMMENT_COL = "DPR Comment"
UNMAPPED_COL = "_unmapped_services"


def _format_date(dt) -> str:
    """Return m/d string (no leading zeros)."""
    if pd.isna(dt) or dt is None:
        return ""
    if hasattr(dt, "month"):
        return f"{dt.month}/{dt.day}"
    return str(dt)


def _format_money(amount: float) -> str:
    """Return $X,XXX.XX string with comma thousands separator."""
    return f"${amount:,.2f}"


def _comment_entry_sort_key(entry: tuple) -> tuple:
    """
    Sort key for the m/d label entries *within* a single MRN's comment string.

    Priority:
      1. Entries with a parseable date sort before entries without one.
      2. Among dated entries: chronological order (earliest first).
      3. For same-date entries: original paste order (lower paste_index first).
      4. Entries without a date: paste order only.

    This function sorts only the TEXT of the comment — it never reorders
    DataFrame rows.
    """
    ts, paste_index, _ = entry
    if ts is None or pd.isna(ts):
        # Group 1 (no date): sort last, by paste order
        return (1, 0, paste_index)
    # Group 0 (has date): sort by Unix seconds, then paste order for ties
    return (0, int(ts.timestamp()), paste_index)


def generate_comments(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """
    Add a DPR Comment column to the DataFrame.

    Row order is guaranteed to be identical to the input (business rule 1 & 4).

    Returns:
        (result_df, warnings, unmapped_service_types)
    """
    if df.empty:
        return df.copy(), [], []

    # Work on an explicit copy; normalise index so paste_index == row position.
    # reset_index(drop=True) renumbers rows 0…N-1 in their current order —
    # it does NOT sort or reorder.
    df = df.copy().reset_index(drop=True)
    original_index = df.index.tolist()   # [0, 1, 2, …] — used for the final assert

    warnings: list[str] = []
    unmapped_services: list[str] = []

    # ── Build per-MRN comments ───────────────────────────────────────────────
    mrn_comments: dict[str, str] = {}
    mrn_unmapped: dict[str, list[str]] = {}

    # Collect MRNs in first-seen order (preserves original paste grouping).
    seen_mrns: list[str] = list(dict.fromkeys(df[COL_MRN].astype(str).tolist()))

    for mrn in seen_mrns:
        mrn_rows = df[df[COL_MRN].astype(str) == mrn]

        # Business rule 2: one total per MRN
        total = mrn_rows[COL_CHARGE].sum()
        money_str = _format_money(total)

        entries: list[tuple] = []
        local_unmapped: list[str] = []

        for paste_index, row in mrn_rows.iterrows():
            dos_parsed = row.get("_dos_parsed", None)
            service_raw = str(row[COL_SERVICE]) if pd.notna(row[COL_SERVICE]) else ""
            label, is_unmapped = map_service(service_raw)

            if is_unmapped and service_raw:
                local_unmapped.append(service_raw)

            date_str = _format_date(dos_parsed)
            entry_text = f"{date_str} {label}".strip() if date_str else label
            entries.append((dos_parsed, paste_index, entry_text))

        # Sort entries for the comment string only — DataFrame rows are untouched.
        entries.sort(key=_comment_entry_sort_key)

        # Business rule 2: exactly one comment per MRN
        comment = f"{money_str} {', '.join(e[2] for e in entries)}"
        mrn_comments[mrn] = comment

        if local_unmapped:
            mrn_unmapped[mrn] = local_unmapped
            unmapped_services.extend(local_unmapped)

    # ── Business rule 3: stamp the same comment on every row for that MRN ───
    # .map() replaces values in-place by label — row order is never changed.
    df[COMMENT_COL] = df[COL_MRN].astype(str).map(mrn_comments)

    # ── Business rule 1 & 4: assert row order is identical to paste order ───
    assert df.index.tolist() == original_index, (
        "BUG: generate_comments altered the DataFrame row order. "
        "Row order must match the original paste order."
    )

    for mrn, svcs in mrn_unmapped.items():
        warnings.append(
            f"MRN {mrn}: unmapped service type(s): {', '.join(repr(s) for s in svcs)}"
        )

    return df, warnings, list(set(unmapped_services))


def comments_only_text(df: pd.DataFrame) -> str:
    """
    Return a newline-delimited string of DPR comments, one line per row,
    in exact paste order (business rule 4). No blank lines.
    """
    if COMMENT_COL not in df.columns:
        return ""
    lines = [str(v) for v in df[COMMENT_COL] if pd.notna(v) and str(v).strip()]
    return "\n".join(lines)


def full_table_text(df: pd.DataFrame) -> str:
    """
    Return the processed DataFrame as tab-delimited text for paste back into
    Excel. Rows are in exact paste order (business rule 4).
    Excludes internal helper columns (prefixed with _).
    """
    export_cols = [c for c in df.columns if not str(c).startswith("_")]
    return df[export_cols].to_csv(sep="\t", index=False, lineterminator="\n")
