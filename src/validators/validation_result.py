"""Validation result dataclass for all validators.

Provides a consistent structure for validation results across all validators.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class ValidationResult:
    """Validation result for any validation check.

    Three-tier structure:
    - errors: Blockers that prevent publishing
    - warnings: Non-blocking issues to address
    - suggestions: Optional improvements
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "metrics": self.metrics
        }
