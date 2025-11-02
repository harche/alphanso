"""Validators for checking build, test, and code quality conditions.

Validators are CONDITIONS that the framework checks (build success, test pass,
no merge conflicts, etc.). They are executed by the framework in the validate_node,
NOT by the AI agent.

This is a critical separation:
- Validators = WHAT we check (run by framework)
- AI Tools = HOW we investigate and fix (used by Claude)
"""

from alphanso.validators.base import Validator
from alphanso.validators.command import CommandValidator
from alphanso.validators.git import GitConflictValidator

__all__ = ["Validator", "CommandValidator", "GitConflictValidator"]
