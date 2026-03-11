"""
Tests for dpr/parser.py — pasted Excel text parsing.
"""

import pytest
import pandas as pd
from dpr.parser import parse_pasted_text, COL_MRN, COL_DOS, COL_SERVICE, COL_CHARGE, COL_CLIENT


HEADER = "Client Name\tMRN\tDate of Service\tService Type\tPayment Date\tCharge Amount\tPayment Type\tReceipt Saved\tComment"


def make_row(**kwargs) -> str:
    """Build a tab-delimited row from keyword args (all 9 columns)."""
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
        defaults["client"],
        defaults["mrn"],
        defaults["dos"],
        defaults["service"],
        defaults["payment_date"],
        defaults["charge"],
        defaults["payment_type"],
        defaults["receipt"],
        defaults["comment"],
    ])


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------
class TestBasicParsing:
    def test_single_row_with_header(self):
        text = HEADER + "\n" + make_row(mrn="10001", charge="175.00")
        result = parse_pasted_text(text)
        assert not result.errors
        assert len(result.df) == 1
        assert result.df[COL_MRN].iloc[0] == "10001"
        assert result.df[COL_CHARGE].iloc[0] == 175.0

    def test_multiple_rows(self):
        text = (
            HEADER + "\n"
            + make_row(mrn="10001", charge="175.00") + "\n"
            + make_row(mrn="10002", charge="200.00")
        )
        result = parse_pasted_text(text)
        assert not result.errors
        assert len(result.df) == 2

    def test_header_detection_case_insensitive(self):
        header = "Client Name\tMRN\tDate Of Service\tService Type\tPayment Date\tCharge Amount\tPayment Type\tReceipt Saved\tComment"
        text = header + "\n" + make_row(mrn="10001")
        result = parse_pasted_text(text)
        assert not result.errors
        assert COL_DOS in result.df.columns

    def test_trailing_space_column_names(self):
        """Column names with trailing spaces should be normalized."""
        header = "Client Name\tMRN\tDate of Service\tService Type\tPayment Date\tCharge Amount \tPayment Type\tReceipt Saved\tComment"
        text = header + "\n" + make_row(mrn="10001", charge="50.00")
        result = parse_pasted_text(text)
        assert not result.errors
        assert COL_CHARGE in result.df.columns
        assert result.df[COL_CHARGE].iloc[0] == 50.0

    def test_receipt_misspelling(self):
        """'Reciept Saved' misspelling should be accepted."""
        header = "Client Name\tMRN\tDate of Service\tService Type\tPayment Date\tCharge Amount\tPayment Type\tReciept Saved\tComment"
        text = header + "\n" + make_row()
        result = parse_pasted_text(text)
        assert not result.errors

    def test_blank_lines_ignored(self):
        text = "\n\n" + HEADER + "\n" + make_row(mrn="10001") + "\n\n"
        result = parse_pasted_text(text)
        assert not result.errors
        assert len(result.df) == 1

    def test_empty_input_returns_error(self):
        result = parse_pasted_text("")
        assert result.errors

    def test_whitespace_only_returns_error(self):
        result = parse_pasted_text("   \n\n  ")
        assert result.errors


# ---------------------------------------------------------------------------
# Column validation
# ---------------------------------------------------------------------------
class TestColumnValidation:
    def test_missing_mrn_column_is_error(self):
        header = "Client Name\tDate of Service\tService Type\tCharge Amount"
        text = header + "\nJohn Doe\t2/23/2024\tOutpatient 53+ minutes\t170.00"
        result = parse_pasted_text(text)
        assert any("MRN" in e for e in result.errors)

    def test_missing_dos_column_is_error(self):
        header = "Client Name\tMRN\tService Type\tCharge Amount"
        text = header + "\nJohn Doe\t10001\tOutpatient 53+ minutes\t170.00"
        result = parse_pasted_text(text)
        assert any("Date of Service" in e for e in result.errors)

    def test_missing_service_type_is_error(self):
        header = "Client Name\tMRN\tDate of Service\tCharge Amount"
        text = header + "\nJohn Doe\t10001\t2/23/2024\t170.00"
        result = parse_pasted_text(text)
        assert any("Service Type" in e for e in result.errors)

    def test_missing_charge_amount_is_error(self):
        header = "Client Name\tMRN\tDate of Service\tService Type"
        text = header + "\nJohn Doe\t10001\t2/23/2024\tOutpatient 53+ minutes"
        result = parse_pasted_text(text)
        assert any("Charge Amount" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Charge parsing
# ---------------------------------------------------------------------------
class TestChargeParsing:
    def test_dollar_sign_stripped(self):
        text = HEADER + "\n" + make_row(charge="$170.00")
        result = parse_pasted_text(text)
        assert not result.errors
        assert result.df[COL_CHARGE].iloc[0] == 170.0

    def test_integer_charge(self):
        text = HEADER + "\n" + make_row(charge="175")
        result = parse_pasted_text(text)
        assert result.df[COL_CHARGE].iloc[0] == 175.0

    def test_float_charge(self):
        text = HEADER + "\n" + make_row(charge="175.5")
        result = parse_pasted_text(text)
        assert result.df[COL_CHARGE].iloc[0] == 175.5

    def test_comma_in_charge(self):
        text = HEADER + "\n" + make_row(charge="1,500.00")
        result = parse_pasted_text(text)
        assert result.df[COL_CHARGE].iloc[0] == 1500.0

    def test_non_numeric_charge_warns(self):
        text = HEADER + "\n" + make_row(charge="N/A")
        result = parse_pasted_text(text)
        assert any("coerced" in w.lower() or "non-numeric" in w.lower() for w in result.warnings)
        assert result.df[COL_CHARGE].iloc[0] == 0.0

    def test_mixed_charge_formats(self):
        text = (
            HEADER + "\n"
            + make_row(mrn="10001", charge="$100.00") + "\n"
            + make_row(mrn="10002", charge="200") + "\n"
            + make_row(mrn="10003", charge="50.5")
        )
        result = parse_pasted_text(text)
        assert result.df[COL_CHARGE].tolist() == [100.0, 200.0, 50.5]


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------
class TestDateParsing:
    def test_m_d_yyyy_format(self):
        text = HEADER + "\n" + make_row(dos="2/3/2024")
        result = parse_pasted_text(text)
        assert result.df["_dos_parsed"].iloc[0].month == 2
        assert result.df["_dos_parsed"].iloc[0].day == 3

    def test_mm_dd_yyyy_format(self):
        text = HEADER + "\n" + make_row(dos="11/21/2024")
        result = parse_pasted_text(text)
        assert result.df["_dos_parsed"].iloc[0].month == 11
        assert result.df["_dos_parsed"].iloc[0].day == 21

    def test_unparseable_date_warns(self):
        text = HEADER + "\n" + make_row(dos="not-a-date")
        result = parse_pasted_text(text)
        assert any("unparseable" in w.lower() or "date" in w.lower() for w in result.warnings)

    def test_blank_date_warns(self):
        text = HEADER + "\n" + make_row(dos="")
        result = parse_pasted_text(text)
        assert any("blank" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------
class TestWarnings:
    def test_multi_row_mrn_warns(self):
        text = (
            HEADER + "\n"
            + make_row(mrn="10001") + "\n"
            + make_row(mrn="10001")
        )
        result = parse_pasted_text(text)
        assert any("10001" in w for w in result.warnings)

    def test_blank_mrn_warns(self):
        text = HEADER + "\n" + make_row(mrn="")
        result = parse_pasted_text(text)
        assert any("blank mrn" in w.lower() for w in result.warnings)
