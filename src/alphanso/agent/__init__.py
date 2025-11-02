"""Agent module for Claude Code Agent SDK integration.

This module provides the ConvergenceAgent class which wraps Claude Code Agent SDK
for AI-assisted investigation and fixing in the convergence loop.
"""

from alphanso.agent.client import ConvergenceAgent
from alphanso.agent.prompts import build_fix_prompt, build_user_message

__all__ = ["ConvergenceAgent", "build_fix_prompt", "build_user_message"]
