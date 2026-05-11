"""Permission review hook for Claude Code.

Uses an LLM sub-agent to review permission requests with project context.
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional


async def review_permission_async(
    tool: Optional[str] = None,
    permission: Optional[str] = None,
    command: Optional[str] = None,
    target: Optional[str] = None,
) -> dict:
    """Review permission using LLM agent."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from agents.permission_reviewer import review_with_llm

    return await review_with_llm(
        permission=permission or "",
        tool_name=tool,
        command=command,
        target=target,
    )


def format_feedback(result: dict) -> str:
    """Format review result as human-readable feedback."""
    decision = result.get("decision", "unknown").upper()
    reason = result.get("reason", "No reason provided")
    suggestion = result.get("suggestion")

    lines = [
        f"[{decision}]",
        f"Reason: {reason}",
    ]
    if suggestion:
        lines.append(f"Consider: {suggestion}")

    return "\n".join(lines)


async def main():
    """CLI entry point for hook integration."""
    tool = None
    permission = None
    command = None
    target = None

    # Parse arguments: tool permission [--command X] [--target Y]
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--command" and i + 1 < len(args):
            command = args[i + 1]
        elif arg == "--target" and i + 1 < len(args):
            target = args[i + 1]
        elif i == 0:
            tool = arg
        elif i == 1:
            permission = arg

    if not permission:
        print("Usage: python hooks.py <tool> <permission> [--command <cmd>] [--target <path>]")
        sys.exit(1)

    # Review the permission
    result = await review_permission_async(tool, permission, command, target)

    # Output based on decision
    decision = result.get("decision", "review")

    if decision == "deny":
        print(f"[DENY] {result.get('reason', 'Operation denied')}")
        if result.get("suggestion"):
            print(f"Suggestion: {result['suggestion']}")
        sys.exit(1)  # Denied - user should not proceed
    elif decision == "review":
        print(f"[REVIEW REQUIRED]")
        print(f"Reason: {result.get('reason', 'Requires human review')}")
        if result.get("suggestion"):
            print(f"Consider: {result['suggestion']}")
        sys.exit(2)  # Review required - user should confirm
    else:
        # Allow - output minimal feedback
        print(f"[ALLOW] {result.get('reason', 'Operation allowed')}")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())