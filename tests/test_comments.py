"""
Tests for dpr/comments.py — DPR comment generation.
"""

import pytest
import pandas as pd
from dpr.parser import parse_pasted_text, COL_MRN, COL_DOS, COL_SERVICE, COL_CHARGE
from dpr.comments import (
    generate_comments,
    comments_only_text,
    full_table_text,
    COMMENT_COL,
)


HEADER = "Client Name\tMRN\tDate of Service\tService Type\tPayment Date\tCharge Amount\tPayment Type\tReceipt Saved\tComment"


def make_row(**kwargs) -> str:
    defaults = {
        "client": "Test Client",
        "mrn": "12345",
        "dos": "2/23/2024",
        "service": "Outpatient 53+ minutes",
        "payment_date": "3/1/2024",
        "charge": "170.00",
        "payment_type": "Insurance",
        "receipt": "Yes",
        "comment": "",
    }
    defaults.update(kwargs)
    return "\t".join([
        defaults["client"], defaults["mrn"], defaults["dos"],
        defaults["service"], defaults["payment_date"], defaults["charge"],
        defaults["payment_type"], defaults["receipt"], defaults["comment"],
    ])


def parse(text: str) -> pd.DataFrame:
    result = parse_pasted_text(text)
    assert not result.errors, f"Parse errors: {result.errors}"
    return result.df


# ---------------------------------------------------------------------------
# Single-row MRN
# ---------------------------------------------------------------------------
class TestSingleRowMRN:
    def test_comment_format(self):
        text = HEADER + "\n" + make_row(mrn="10001", dos="2/23/2024", service="Outpatient 16-37 minutes", charge="24.00")
        df = parse(text)
        out_df, warnings, unmapped = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert comment == "$24.00 2/23 IT 16-37"

    def test_iop_comment(self):
        text = HEADER + "\n" + make_row(mrn="10002", dos="2/23/2024", service="IOP Chappaqua", charge="170.00")
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        assert out_df[COMMENT_COL].iloc[0] == "$170.00 2/23 IOP"

    def test_tele_comment(self):
        text = HEADER + "\n" + make_row(mrn="10003", dos="2/23/2024", service="Telemed: Outpatient 53+ minutes", charge="170.00")
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        assert out_df[COMMENT_COL].iloc[0] == "$170.00 2/23 Tele IT 53+"

    def test_money_format_two_decimals(self):
        text = HEADER + "\n" + make_row(mrn="10004", dos="2/3/2024", service="Outpatient 53+ minutes", charge="725")
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        assert out_df[COMMENT_COL].iloc[0].startswith("$725.00")

    def test_date_no_leading_zeros(self):
        """Date in comment should be m/d not mm/dd."""
        text = HEADER + "\n" + make_row(mrn="10005", dos="2/3/2024", service="Outpatient 53+ minutes", charge="100.00")
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert "2/3" in comment
        assert "02/03" not in comment


# ---------------------------------------------------------------------------
# Duplicate MRN — 2 rows
# ---------------------------------------------------------------------------
class TestDuplicateMRNTwoRows:
    def test_comment_repeats_on_both_rows(self):
        text = (
            HEADER + "\n"
            + make_row(mrn="10001", dos="2/23/2024", service="IOP Chappaqua", charge="85.00") + "\n"
            + make_row(mrn="10001", dos="2/23/2024", service="Telemed: Outpatient 53+ minutes", charge="85.00")
        )
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        assert out_df[COMMENT_COL].iloc[0] == out_df[COMMENT_COL].iloc[1]

    def test_charge_summed(self):
        text = (
            HEADER + "\n"
            + make_row(mrn="10001", dos="2/23/2024", service="IOP Chappaqua", charge="85.00") + "\n"
            + make_row(mrn="10001", dos="2/23/2024", service="Telemed: Outpatient 53+ minutes", charge="85.00")
        )
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert comment.startswith("$170.00")

    def test_both_services_in_comment(self):
        text = (
            HEADER + "\n"
            + make_row(mrn="10001", dos="2/23/2024", service="IOP Chappaqua", charge="85.00") + "\n"
            + make_row(mrn="10001", dos="2/23/2024", service="Telemed: Outpatient 53+ minutes", charge="85.00")
        )
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert "IOP" in comment
        assert "Tele IT 53+" in comment


# ---------------------------------------------------------------------------
# Duplicate MRN — 6+ rows
# ---------------------------------------------------------------------------
class TestDuplicateMRNManyRows:
    def _build_text(self) -> str:
        rows = [HEADER]
        services_charges = [
            ("11/21/2024", "Telemed: Assessment/Diag (BPS) w/o med services", "200.00"),
            ("12/10/2024", "Outpatient Group (75-90 minutes)", "175.00"),
            ("2/18/2025", "Outpatient Group (75-90 minutes)", "175.00"),
            ("2/25/2025", "Outpatient Group (75-90 minutes)", "175.00"),
            ("3/4/2025", "Outpatient Group (75-90 minutes)", "175.00"),
            ("3/11/2025", "Outpatient 53+ minutes", "175.00"),
        ]
        for dos, svc, chg in services_charges:
            rows.append(make_row(mrn="99999", dos=dos, service=svc, charge=chg))
        return "\n".join(rows)

    def test_comment_repeats_on_all_rows(self):
        df = parse(self._build_text())
        out_df, _, _ = generate_comments(df)
        comments = out_df[COMMENT_COL].tolist()
        assert len(set(comments)) == 1, "All rows for same MRN must have identical comment"

    def test_charge_total(self):
        df = parse(self._build_text())
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert comment.startswith("$1,075.00")

    def test_chronological_order_in_comment(self):
        df = parse(self._build_text())
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        # Tele Assess from 11/21 should appear before group entries from 12/10
        pos_assess = comment.index("Tele Assess")
        pos_group = comment.index("group")
        assert pos_assess < pos_group

    def test_example_from_spec(self):
        """$725.00 11/21 Tele Assess, 12/10 group, 2/18 group"""
        rows = [HEADER]
        services = [
            ("11/21/2024", "Telemed: Assessment/Diag (BPS) w/o med services", "275.00"),
            ("12/10/2024", "Outpatient Group (75-90 minutes)", "225.00"),
            ("2/18/2025", "Outpatient Group (75-90 minutes)", "225.00"),
        ]
        for dos, svc, chg in services:
            rows.append(make_row(mrn="77777", dos=dos, service=svc, charge=chg))
        df = parse("\n".join(rows))
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert comment == "$725.00 11/21 Tele Assess, 12/10 group, 2/18 group"


# ---------------------------------------------------------------------------
# NSF rows
# ---------------------------------------------------------------------------
class TestNSFRows:
    def test_nsf_in_comment(self):
        text = HEADER + "\n" + make_row(mrn="10001", dos="3/5/2024", service="NSF - Outpatient Group (75-90 minutes)", charge="-175.00")
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert "NSF group" in comment

    def test_nsf_tele_in_comment(self):
        text = HEADER + "\n" + make_row(mrn="10001", dos="3/5/2024", service="NSF -Telemed OP: Psych Appointment (30-39 minutes)", charge="-100.00")
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert "NSF Tele Psych f/u 30-39" in comment


# ---------------------------------------------------------------------------
# Row order preservation
# ---------------------------------------------------------------------------
class TestRowOrderPreservation:
    def test_original_row_order_preserved(self):
        """Rows must stay in original input order even after grouping."""
        text = (
            HEADER + "\n"
            + make_row(mrn="AAA", dos="2/23/2024", service="Outpatient 53+ minutes", charge="100.00") + "\n"
            + make_row(mrn="BBB", dos="1/15/2024", service="Outpatient 16-37 minutes", charge="50.00") + "\n"
            + make_row(mrn="CCC", dos="3/10/2024", service="Outpatient 38-52 minutes", charge="75.00")
        )
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        assert out_df[COL_MRN].tolist() == ["AAA", "BBB", "CCC"]

    def test_same_date_same_mrn_preserves_paste_order(self):
        """Same MRN + same date: preserve original paste order."""
        text = (
            HEADER + "\n"
            + make_row(mrn="MRN1", dos="2/23/2024", service="IOP Chappaqua", charge="85.00") + "\n"
            + make_row(mrn="MRN1", dos="2/23/2024", service="Telemed: Outpatient 53+ minutes", charge="85.00")
        )
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        # IOP was pasted first, so should appear before Tele IT 53+ in comment
        pos_iop = comment.index("IOP")
        pos_tele = comment.index("Tele IT 53+")
        assert pos_iop < pos_tele


# ---------------------------------------------------------------------------
# Copy output helpers
# ---------------------------------------------------------------------------
class TestCopyHelpers:
    def _get_processed(self) -> pd.DataFrame:
        text = (
            HEADER + "\n"
            + make_row(mrn="10001", dos="2/23/2024", service="Outpatient 16-37 minutes", charge="24.00") + "\n"
            + make_row(mrn="10001", dos="2/23/2024", service="Telemed: Outpatient 53+ minutes", charge="146.00") + "\n"
            + make_row(mrn="10002", dos="3/5/2024", service="IOP Chappaqua", charge="200.00")
        )
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        return out_df

    def test_comments_only_text_line_count(self):
        out_df = self._get_processed()
        text = comments_only_text(out_df)
        lines = [l for l in text.splitlines() if l.strip()]
        assert len(lines) == 3  # 3 rows

    def test_comments_only_no_blank_lines(self):
        out_df = self._get_processed()
        text = comments_only_text(out_df)
        blank_lines = [l for l in text.splitlines() if not l.strip()]
        assert not blank_lines

    def test_full_table_has_header(self):
        out_df = self._get_processed()
        text = full_table_text(out_df)
        first_line = text.splitlines()[0]
        assert COMMENT_COL in first_line

    def test_full_table_row_count(self):
        out_df = self._get_processed()
        text = full_table_text(out_df)
        lines = [l for l in text.splitlines() if l.strip()]
        # header + 3 data rows
        assert len(lines) == 4

    def test_full_table_no_internal_columns(self):
        out_df = self._get_processed()
        text = full_table_text(out_df)
        first_line = text.splitlines()[0]
        assert "_dos_parsed" not in first_line
        assert "_unmapped" not in first_line


# ---------------------------------------------------------------------------
# Unmapped service fallback
# ---------------------------------------------------------------------------
class TestUnmappedService:
    def test_unmapped_service_preserved_in_comment(self):
        weird_service = "Weird Unlisted Service"
        text = HEADER + "\n" + make_row(mrn="10001", dos="2/23/2024", service=weird_service, charge="100.00")
        df = parse(text)
        out_df, warnings, unmapped = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert weird_service in comment

    def test_unmapped_service_flagged_in_warnings(self):
        weird_service = "Weird Unlisted Service"
        text = HEADER + "\n" + make_row(mrn="10001", dos="2/23/2024", service=weird_service, charge="100.00")
        df = parse(text)
        _, warnings, unmapped = generate_comments(df)
        assert any("unmapped" in w.lower() for w in warnings)
        assert weird_service in unmapped


# ---------------------------------------------------------------------------
# Empty pane
# ---------------------------------------------------------------------------
class TestEmptyPane:
    def test_empty_df_returns_empty(self):
        out_df, warnings, unmapped = generate_comments(pd.DataFrame())
        assert out_df.empty
        assert warnings == []
        assert unmapped == []

    def test_comments_only_empty_df(self):
        result = comments_only_text(pd.DataFrame())
        assert result == ""

    def test_full_table_empty_df(self):
        result = full_table_text(pd.DataFrame())
        assert result == "\n" or result == ""  # empty csv


# ---------------------------------------------------------------------------
# Mixed charges
# ---------------------------------------------------------------------------
class TestMixedChargeFormats:
    def test_dollar_and_plain_and_float(self):
        text = (
            HEADER + "\n"
            + make_row(mrn="10001", dos="2/1/2024", service="Outpatient 53+ minutes", charge="$100.00") + "\n"
            + make_row(mrn="10001", dos="2/2/2024", service="Outpatient 53+ minutes", charge="200") + "\n"
            + make_row(mrn="10001", dos="2/3/2024", service="Outpatient 53+ minutes", charge="50.5")
        )
        df = parse(text)
        out_df, _, _ = generate_comments(df)
        comment = out_df[COMMENT_COL].iloc[0]
        assert comment.startswith("$350.50")


# ---------------------------------------------------------------------------
# Explicit business-rule tests
# ---------------------------------------------------------------------------
class TestBusinessRules:
    """
    Four rules stated explicitly in the requirements:
      1. Row order must never change.
      2. Each MRN gets one calculated comment.
      3. That comment is written onto every row with that MRN.
      4. Comments must align exactly with pasted row order for Excel paste-back.
    """

    def _build_interleaved(self) -> str:
        """
        Rows interleaved across three MRNs in a specific paste order:
        AAA, BBB, AAA, CCC, BBB
        """
        return (
            HEADER + "\n"
            + make_row(mrn="AAA", dos="3/1/2024", service="Outpatient 53+ minutes",    charge="100.00") + "\n"
            + make_row(mrn="BBB", dos="1/15/2024", service="Outpatient 16-37 minutes", charge="50.00")  + "\n"
            + make_row(mrn="AAA", dos="3/5/2024",  service="IOP Chappaqua",            charge="200.00") + "\n"
            + make_row(mrn="CCC", dos="2/20/2024", service="Outpatient 38-52 minutes", charge="75.00")  + "\n"
            + make_row(mrn="BBB", dos="2/1/2024",  service="Outpatient 38-52 minutes", charge="80.00")
        )

    # Rule 1: Row order must never change
    def test_rule1_row_order_never_changes(self):
        df = parse(self._build_interleaved())
        out_df, _, _ = generate_comments(df)
        # Output MRN sequence must match paste order exactly
        assert out_df[COL_MRN].tolist() == ["AAA", "BBB", "AAA", "CCC", "BBB"]

    # Rule 2: Each MRN gets exactly one calculated comment
    def test_rule2_each_mrn_gets_one_comment(self):
        df = parse(self._build_interleaved())
        out_df, _, _ = generate_comments(df)
        # Every row for the same MRN must carry an identical comment string
        for mrn in ["AAA", "BBB", "CCC"]:
            mrn_comments = out_df.loc[out_df[COL_MRN] == mrn, COMMENT_COL].tolist()
            assert len(set(mrn_comments)) == 1, (
                f"MRN {mrn} has {len(set(mrn_comments))} distinct comments — expected 1"
            )

    # Rule 3: That comment is written onto every row with that MRN
    def test_rule3_comment_written_on_every_row(self):
        df = parse(self._build_interleaved())
        out_df, _, _ = generate_comments(df)
        # No row may have a missing/blank DPR comment
        assert out_df[COMMENT_COL].notna().all()
        assert (out_df[COMMENT_COL].astype(str).str.strip() != "").all()
        # AAA has 2 rows — both must carry the same comment
        aaa_rows = out_df[out_df[COL_MRN] == "AAA"]
        assert aaa_rows.shape[0] == 2
        assert aaa_rows[COMMENT_COL].iloc[0] == aaa_rows[COMMENT_COL].iloc[1]

    # Rule 4: Comments align exactly with pasted row order for Excel paste-back
    def test_rule4_comments_only_text_matches_paste_order(self):
        df = parse(self._build_interleaved())
        out_df, _, _ = generate_comments(df)
        comments_text = comments_only_text(out_df)
        comment_lines = comments_text.splitlines()
        # One line per row
        assert len(comment_lines) == 5
        # The comments are in paste row order: AAA, BBB, AAA, CCC, BBB
        # AAA rows share the same comment; BBB rows share the same comment.
        assert comment_lines[0] == comment_lines[2]   # both AAA rows
        assert comment_lines[1] == comment_lines[4]   # both BBB rows
        assert comment_lines[0] != comment_lines[1]   # AAA ≠ BBB
        assert comment_lines[0] != comment_lines[3]   # AAA ≠ CCC

    def test_rule4_full_table_text_matches_paste_order(self):
        df = parse(self._build_interleaved())
        out_df, _, _ = generate_comments(df)
        table_text = full_table_text(out_df)
        lines = [l for l in table_text.splitlines() if l.strip()]
        # header + 5 data rows
        assert len(lines) == 6
        # MRN column (second tab-delimited field) must follow paste order
        data_mrns = [line.split("\t")[1] for line in lines[1:]]
        assert data_mrns == ["AAA", "BBB", "AAA", "CCC", "BBB"]
