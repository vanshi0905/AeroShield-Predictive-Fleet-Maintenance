"""Unit tests for standalone cryptographic audit verification script (scripts/verify_audit.py)."""

import os
import pytest
from scripts.verify_audit import verify_audit, verify_all_subsets


def test_verify_audit_fd001():
    """Verify that FD001 audit ledger passes cryptographic verification."""
    result = verify_audit("FD001")
    assert result is True


def test_verify_all_subsets():
    """Verify that all available subsets (FD001-FD004) pass multi-subset verification."""
    result = verify_all_subsets()
    assert result is True


def test_verify_audit_missing_database():
    """Verify that a non-existent subset returns False cleanly without crashing."""
    result = verify_audit("NON_EXISTENT_SUBSET")
    assert result is False
