"""Prompt builders for Claude Code Agent SDK.

This module provides functions to build system prompts and user messages
that explain validation failures to Claude and request fixes.
"""

from alphanso.graph.state import ConvergenceState


def build_fix_prompt(
    state: ConvergenceState, custom_prompt: str | None = None
) -> str:
    """Build system prompt for AI fix node.

    Optionally starts with custom prompt defining agent's role/task,
    then adds convergence loop context with validation failures.

    Args:
        state: Current convergence state
        custom_prompt: Optional custom prompt defining agent role/task
                      (e.g., "You are a Kubernetes rebasing agent...")

    Returns:
        Complete system prompt with custom prefix + convergence context
    """
    # Start with custom prompt if provided
    prompt = custom_prompt.strip() + "\n\n---\n\n" if custom_prompt else ""

    # Add convergence loop context
    attempt = state.get("attempt", 0)
    max_attempts = state.get("max_attempts", 10)
    failed = state.get("failed_validators", [])

    prompt += f"""Attempt: {attempt + 1}/{max_attempts}

IMPORTANT: The framework runs validators (make, make test, etc.) and reports results to you.
Your job is to investigate WHY they failed and FIX the issues using the tools available to you.

Failed Validators (run by framework, not you):
{', '.join(failed) if failed else 'None'}

You have access to investigation and fixing tools from the SDK. Use whatever tools are needed
to understand the failures and apply fixes. The framework will re-run validators after you're done.

Previous attempts:
"""

    # Add failure history
    for i, history in enumerate(state.get("failure_history", [])):
        prompt += f"\nAttempt {i + 1}:\n"
        for result in history:
            if not result.get("success", True):
                validator_name = result.get("validator_name", "Unknown")
                output = result.get("output", "")
                prompt += f"  - {validator_name}: {output[:200]}\n"

    return prompt


def build_user_message(state: ConvergenceState) -> str:
    """Build user message with current failure details.

    Shows only the relevant failures based on context:
    - First AI call (no validator results): Shows main script error
    - Refinement calls (validators failed): Shows only validator errors

    Args:
        state: Current convergence state

    Returns:
        User message with formatted failure details
    """
    validation_results = state.get("validation_results", [])
    failed_validators = [r for r in validation_results if not r.get("success", True)]

    # If validators failed, show ONLY validator errors (refinement mode)
    # Don't show main script error - AI already tried to fix that
    if failed_validators:
        message = "## Validators Failed After Your Previous Fix\n\n"

        for result in failed_validators:
            message += f"### Validator: {result.get('validator_name', 'Unknown')}\n"
            message += f"Exit Code: {result.get('exit_code', 'N/A')}\n"

            # Include the command that was executed
            command = result.get('metadata', {}).get('command', '')
            if command:
                message += f"Command: `{command}`\n"

            message += "\n"

            # Include stdout (truncated to last N lines)
            output = result.get('output', '')
            if output:
                message += f"Output (last {output.count(chr(10))} lines):\n```\n{output}\n```\n\n"

            # Include stderr (full, usually has the important errors)
            stderr = result.get("stderr", "")
            if stderr:
                message += f"Stderr:\n```\n{stderr}\n```\n\n"

        message += "Please refine your approach to fix these validation failures."
    else:
        # First AI call: show only main script error
        main_script_result = state.get("main_script_result")
        if main_script_result and not main_script_result.get("success", True):
            message = "## Main Script Failed\n\n"
            message += f"**Description:** {state.get('main_script_config', {}).get('description', 'Main script')}\n"

            command = main_script_result.get('command', '')
            if command:
                message += f"**Command:** `{command}`\n"

            exit_code = main_script_result.get('exit_code', 'N/A')
            message += f"**Exit Code:** {exit_code}\n\n"

            # Include stderr (usually has the important errors like merge conflicts)
            stderr = main_script_result.get("stderr", "")
            if stderr:
                message += f"**Error Output:**\n```\n{stderr}\n```\n\n"

            # Include stdout if available
            output = main_script_result.get('output', '')
            if output:
                message += f"**Standard Output:**\n```\n{output}\n```\n\n"

            message += "Please investigate the main script failure and apply fixes."
        else:
            # Fallback if no failures found
            message = "Please investigate and fix the issues."

    return message
