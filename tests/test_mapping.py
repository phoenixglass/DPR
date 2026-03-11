"""
Tests for dpr/mapping.py — service-type → DPR shorthand mapping.
"""

import pytest
from dpr.mapping import map_service


# ---------------------------------------------------------------------------
# Standard labels
# ---------------------------------------------------------------------------
class TestStandardMappings:
    def test_assess(self):
        label, unmapped = map_service("Assessment/Diag (BPS) w/o med services")
        assert label == "Assess"
        assert not unmapped

    def test_group(self):
        label, unmapped = map_service("Outpatient Group (75-90 minutes)")
        assert label == "group"
        assert not unmapped

    def test_it_53_plus_with_minutes(self):
        label, unmapped = map_service("Outpatient 53+ minutes")
        assert label == "IT 53+"
        assert not unmapped

    def test_it_53_plus_bare(self):
        label, unmapped = map_service("Outpatient 53+")
        assert label == "IT 53+"
        assert not unmapped

    def test_it_38_52(self):
        label, unmapped = map_service("Outpatient 38-52 minutes")
        assert label == "IT 38-52"
        assert not unmapped

    def test_it_16_37(self):
        label, unmapped = map_service("Outpatient 16-37 minutes")
        assert label == "IT 16-37"
        assert not unmapped

    def test_emdr_53_plus(self):
        label, unmapped = map_service("Outpatient EMDR 53+ minutes")
        assert label == "IT 53+"
        assert not unmapped

    def test_psych_fu_30_39(self):
        label, unmapped = map_service("OP: Psych Appointment (30-39 minutes)")
        assert label == "Psych f/u 30-39"
        assert not unmapped

    def test_psych_eval_psychiatric(self):
        label, unmapped = map_service("Psychiatric Diag. Eval. W. Med Services")
        assert label == "Psych Eval"
        assert not unmapped

    def test_psych_eval_psych(self):
        label, unmapped = map_service("Psych Diag. Eval. W. Med Services")
        assert label == "Psych Eval"
        assert not unmapped

    def test_mat(self):
        label, unmapped = map_service("Medication Admin/Injection")
        assert label == "MAT"
        assert not unmapped

    def test_mat_plus_psych(self):
        label, unmapped = map_service("OP: Psych with Medication Admin/Injection")
        assert label == "MAT + Psych f/u"
        assert not unmapped

    def test_ft_with_client(self):
        label, unmapped = map_service("Family Session with Client 26+ minutes")
        assert label == "FT w/client"
        assert not unmapped

    def test_ft_without_client(self):
        label, unmapped = map_service("Family Session w/out the Client 26+ minutes")
        assert label == "FT w/out client"
        assert not unmapped

    def test_iop_wilton(self):
        label, unmapped = map_service("IOP-Wilton")
        assert label == "IOP"
        assert not unmapped

    def test_iop_chappaqua(self):
        label, unmapped = map_service("IOP Chappaqua")
        assert label == "IOP"
        assert not unmapped

    def test_iop_huntington(self):
        label, unmapped = map_service("IOP Huntington")
        assert label == "IOP"
        assert not unmapped

    def test_iop_bare(self):
        label, unmapped = map_service("IOP")
        assert label == "IOP"
        assert not unmapped

    def test_payment_plan(self):
        label, unmapped = map_service("payment plan")
        assert label == "payment plan"
        assert not unmapped


# ---------------------------------------------------------------------------
# Telemed rules
# ---------------------------------------------------------------------------
class TestTelemedMappings:
    def test_tele_it_53_plus(self):
        label, unmapped = map_service("Telemed: Outpatient 53+ minutes")
        assert label == "Tele IT 53+"
        assert not unmapped

    def test_tele_it_38_52(self):
        label, unmapped = map_service("Telemed: Outpatient 38-52 minutes")
        assert label == "Tele IT 38-52"
        assert not unmapped

    def test_tele_it_16_37(self):
        label, unmapped = map_service("Telemed: Outpatient 16-37 minutes")
        assert label == "Tele IT 16-37"
        assert not unmapped

    def test_tele_group(self):
        label, unmapped = map_service("Telemed: Outpatient Group (75-90 minutes)")
        assert label == "Tele group"
        assert not unmapped

    def test_tele_iop(self):
        label, unmapped = map_service("Telemed: IOP")
        assert label == "Tele IOP"
        assert not unmapped

    def test_tele_op_psych_fu(self):
        label, unmapped = map_service("Telemed OP: Psych Appointment (30-39 minutes)")
        assert label == "Tele Psych f/u 30-39"
        assert not unmapped

    def test_tele_assess(self):
        label, unmapped = map_service("Telemed: Assessment/Diag (BPS) w/o med services")
        assert label == "Tele Assess"
        assert not unmapped

    def test_tele_psych_eval(self):
        label, unmapped = map_service("Telemed: Psych Diag. Eval. W. Med Services")
        assert label == "Tele Psych Eval"
        assert not unmapped

    def test_tele_ft_with_client(self):
        label, unmapped = map_service("Telemed: Family Session with client 26+ minutes")
        assert label == "Tele FT w/client"
        assert not unmapped

    def test_tele_ft_without_client(self):
        label, unmapped = map_service("Telemed: Family Session w/out the Client 26+ minutes")
        assert label == "Tele FT w/out client"
        assert not unmapped


# ---------------------------------------------------------------------------
# NSF rules
# ---------------------------------------------------------------------------
class TestNSFMappings:
    def test_nsf_group(self):
        label, unmapped = map_service("NSF - Outpatient Group (75-90 minutes)")
        assert label == "NSF group"
        assert not unmapped

    def test_nsf_it_53_plus(self):
        label, unmapped = map_service("NSF - Outpatient 53+")
        assert label == "NSF IT 53+"
        assert not unmapped

    def test_nsf_iop_chappaqua(self):
        label, unmapped = map_service("NSF - IOP Chappaqua")
        assert label == "NSF IOP"
        assert not unmapped

    def test_nsf_no_space_after_dash(self):
        """NSF -Telemed OP: Psych Appointment — both NSF and Telemed"""
        label, unmapped = map_service("NSF -Telemed OP: Psych Appointment (30-39 minutes)")
        assert label == "NSF Tele Psych f/u 30-39"
        assert not unmapped

    def test_nsf_tele_it_53_plus(self):
        label, unmapped = map_service("NSF - Telemed: Outpatient 53+ minutes")
        assert label == "NSF Tele IT 53+"
        assert not unmapped


# ---------------------------------------------------------------------------
# Fallback / unmapped
# ---------------------------------------------------------------------------
class TestUnmapped:
    def test_unknown_service(self):
        label, unmapped = map_service("Some weird service not in the list")
        assert unmapped is True
        assert "Some weird service not in the list" in label

    def test_empty_string(self):
        label, unmapped = map_service("")
        assert label == ""
        assert unmapped is True

    def test_none_like(self):
        label, unmapped = map_service(None)  # type: ignore[arg-type]
        assert label == ""
        assert unmapped is True
