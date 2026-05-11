"""Spec compliance checker - validates actions against active spec scope."""
from .checker import (
    SpecScope,
    SpecComplianceChecker,
    ComplianceResult,
    get_compliance_checker,
    check_compliance,
    FRONTMATTER_TEMPLATE,
)

__all__ = [
    "SpecScope",
    "SpecComplianceChecker",
    "ComplianceResult",
    "get_compliance_checker",
    "check_compliance",
    "FRONTMATTER_TEMPLATE",
]
